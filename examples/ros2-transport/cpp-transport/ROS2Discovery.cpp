// -*- C++ -*-
/*!
 * @file  ROS2Discovery.cpp
 * @brief ROS 2 graph announcements over DDS
 */

#include "ROS2Discovery.h"

#include <rtm/ByteData.h>
#include <rtm/Manager.h>
#include <fastcdr/Cdr.h>
#include <fastcdr/FastBuffer.h>

#ifdef OPENRTM_USE_FASTDDS
#include "FastDDS/CORBACdrDataPubSubTypes.h"
#include "FastDDS/FastDDSManager.h"
#include "FastDDS/DDSEndpoints.h"
#include <fastdds/dds/domain/DomainParticipant.hpp>
#include <fastdds/dds/publisher/DataWriter.hpp>
#include <fastdds/dds/publisher/Publisher.hpp>
#include <fastdds/dds/topic/TypeSupport.hpp>
#else
#include "FastRTPS/CORBACdrDataPubSubTypes.h"
#include "FastRTPS/FastRTPSManager.h"
#include "FastRTPS/DDSEndpoints.h"
#include <fastrtps/Domain.h>
#include <fastrtps/participant/Participant.h>
#include <fastrtps/publisher/Publisher.h>
#endif

#include <iostream>
#include <memory>
#include <regex>
#include <set>
#include <stdexcept>
#include <string>

namespace openrtm_ros2 {
namespace {

#ifdef OPENRTM_USE_FASTDDS
using namespace openrtm_fastdds;
namespace dds = eprosima::fastdds::dds;
#else
using namespace openrtm_fastrtps;
namespace dds = eprosima::fastrtps;
#endif

struct Graph
{
  std::string name;
  std::string name_space;
  Guid participant{};
  std::set<Guid> readers;
  std::set<Guid> writers;
#ifdef OPENRTM_USE_FASTDDS
  dds::DomainParticipant* native_participant = nullptr;
  dds::TypeSupport type{};
  dds::Topic* topic = nullptr;
  dds::Publisher* native_publisher = nullptr;
  dds::DataWriter* publisher = nullptr;
#else
  std::unique_ptr<RTC::CORBACdrDataPubSubType> type;
  dds::Publisher* publisher = nullptr;
#endif

  /*!
   * @if jp
   * @brief 現在のノード情報を DDS で配信する
   * @param present ノードを掲載する場合は true、取り下げる場合は false
   * @else
   * @brief Publish the current node information over DDS
   * @param present True to advertise the node, false to withdraw it
   * @endif
   */
  void announce(bool present) const
  {
    if (!publisher) {
      return;
    }
    // Jazzy rmw_dds_common/msg/ParticipantEntitiesInfo in plain CDR:
    // participant GUID, sequence of nodes, then each node's reader/writer GUIDs.
    eprosima::fastcdr::FastBuffer buffer;
    using namespace eprosima::fastcdr;
    Cdr cdr(buffer, Cdr::LITTLE_ENDIANNESS, CdrVersion::XCDRv1);
    cdr.set_encoding_flag(EncodingAlgorithmFlag::PLAIN_CDR);
    cdr.serialize_encapsulation();
    cdr.serialize_array(participant.data(), participant.size());
    cdr << std::uint32_t(present ? 1 : 0);
    if (present) {
      cdr << name_space << name;
      for (const auto* endpoints : {&readers, &writers}) {
        cdr << static_cast<std::uint32_t>(endpoints->size());
        for (const auto& guid : *endpoints) {
          cdr.serialize_array(guid.data(), guid.size());
        }
      }
    }
    RTC::ByteData sample;
    sample.writeData(reinterpret_cast<unsigned char*>(buffer.getBuffer()),
                     cdr.get_serialized_data_length());
#ifdef OPENRTM_USE_FASTDDS
    if (publisher->write(&sample) != dds::RETCODE_OK) {
#else
    if (!publisher->write(&sample)) {
#endif
      throw std::runtime_error("DDS ros_discovery_info write failed");
    }
  }
};

Graph graph;

/*!
 * @if jp
 * @brief DDS 端点の変更を ROS 2 グラフに反映する
 * @param event 追加、削除、または終了
 * @param kind 端点の方向
 * @param guid 端点の GUID
 * @param marshaling シリアライザ名
 * @else
 * @brief Apply a DDS endpoint change to the ROS 2 graph
 * @param event Addition, removal, or shutdown
 * @param kind Endpoint direction
 * @param guid Endpoint GUID
 * @param marshaling Serializer name
 * @endif
 */
void endpoint_changed(Event event, Kind kind, const Guid& guid, const std::string& marshaling)
{
  try {
    if (event == Event::shutdown) {
      try {
        graph.announce(false);
      } catch (const std::exception&) {
        // Participant removal also removes the graph entries.
      }
#ifdef OPENRTM_USE_FASTDDS
      graph.native_publisher->delete_datawriter(graph.publisher);
      graph.native_participant->delete_publisher(graph.native_publisher);
      graph.native_participant->delete_topic(graph.topic);
      graph.native_participant->unregister_type(graph.type.get_type_name());
#else
      dds::Domain::removePublisher(graph.publisher);
#endif
      graph.publisher = nullptr;
      graph.readers.clear();
      graph.writers.clear();
    } else if (marshaling.compare(0, 5, "ros2:") == 0) {
      auto& endpoints = kind == Kind::reader ? graph.readers : graph.writers;
      if (event == Event::added) {
        endpoints.insert(guid);
      } else {
        endpoints.erase(guid);
      }
      graph.announce(true);
    }
  } catch (const std::exception& error) {
    std::cerr << "ROS2Discovery: " << error.what() << std::endl;
  }
}

}  // namespace

void start_discovery(RTC::Manager& manager)
{
  graph.name = manager.getConfig().getProperty("ros2.node.name");
  if (graph.name.empty() || graph.publisher) {
    return;
  }
  graph.name_space = manager.getConfig().getProperty("ros2.node.namespace", "/");
  if (graph.name.size() > 256 || graph.name_space.size() > 256
      || !std::regex_match(graph.name, std::regex("[A-Za-z_][A-Za-z_0-9]*"))
      || !std::regex_match(graph.name_space, std::regex("/([A-Za-z_][A-Za-z_0-9]*(/[A-Za-z_][A-Za-z_0-9]*)*)?"))) {
    throw std::invalid_argument("Invalid ROS 2 node name or namespace");
  }
  const char* type_name = "rmw_dds_common::msg::dds_::ParticipantEntitiesInfo_";
#ifdef OPENRTM_USE_FASTDDS
  auto* participant = RTC::FastDDSManager::instance().getParticipant();
  if (!participant) {
    throw std::runtime_error("FastDDSTransport has no DDS participant");
  }
  graph.participant = guid_bytes(participant->guid());
  graph.native_participant = participant;
  auto* type = new RTC::CORBACdrDataPubSubType();
  type->init(type_name, true);
  graph.type = dds::TypeSupport(type);
  if (graph.type.register_type(participant) != dds::RETCODE_OK) {
    throw std::runtime_error("Cannot register the DDS ros_discovery_info type");
  }
  graph.topic = participant->create_topic("ros_discovery_info", type_name, dds::TOPIC_QOS_DEFAULT);
  graph.native_publisher = participant->create_publisher(dds::PUBLISHER_QOS_DEFAULT);
  dds::DataWriterQos qos;
  qos.history().depth = 1;
  qos.reliability().kind = dds::RELIABLE_RELIABILITY_QOS;
  qos.durability().kind = dds::TRANSIENT_LOCAL_DURABILITY_QOS;
  qos.endpoint().history_memory_policy = eprosima::fastdds::rtps::PREALLOCATED_WITH_REALLOC_MEMORY_MODE;
  if (graph.topic && graph.native_publisher) {
    graph.publisher = graph.native_publisher->create_datawriter(graph.topic, qos);
  }
  if (!graph.publisher) {
    if (graph.native_publisher) {
      participant->delete_publisher(graph.native_publisher);
    }
    if (graph.topic) {
      participant->delete_topic(graph.topic);
    }
    participant->unregister_type(type_name);
    throw std::runtime_error("Cannot create DDS ros_discovery_info writer");
  }
#else
  auto* participant = RTC::FastRTPSManager::instance().getParticipant();
  if (!participant) {
    throw std::runtime_error("FastRTPSTransport has no DDS participant");
  }
  graph.participant = guid_bytes(participant->getGuid());
  graph.type = std::make_unique<RTC::CORBACdrDataPubSubType>();
  graph.type->init(type_name, true);
  if (!dds::Domain::registerType(participant, graph.type.get())) {
    throw std::runtime_error("Cannot register the DDS ros_discovery_info type");
  }
  dds::PublisherAttributes attributes;
  attributes.topic.topicName = "ros_discovery_info";
  attributes.topic.topicDataType = type_name;
  attributes.topic.historyQos.kind = dds::KEEP_LAST_HISTORY_QOS;
  attributes.topic.historyQos.depth = 1;
  attributes.historyMemoryPolicy = dds::rtps::PREALLOCATED_WITH_REALLOC_MEMORY_MODE;
  attributes.qos.m_reliability.kind = dds::RELIABLE_RELIABILITY_QOS;
  attributes.qos.m_durability.kind = dds::TRANSIENT_LOCAL_DURABILITY_QOS;
  graph.publisher = dds::Domain::createPublisher(participant, attributes);
  if (!graph.publisher) {
    throw std::runtime_error("Cannot create DDS ros_discovery_info publisher");
  }
#endif
  graph.announce(true);
  observe(endpoint_changed);
}

}  // namespace openrtm_ros2
