// -*- C++ -*-
/*!
 * @file  ROS2TransportNamed.cpp
 * @brief Named ROS 2 transport module entry point
 */

#include "ROS2Discovery.h"

// Use the upstream serializers with the FastRTPSTransport factories.
extern "C" void ROS2SerializerInit(RTC::Manager*);

/*!
 * @if jp
 * @brief ROS 2 ノード通知とシリアライザを初期化する
 * @param manager モジュールをロードした RTC Manager
 * @else
 * @brief Initialize ROS 2 node discovery and serializers
 * @param manager RTC Manager that loaded the module
 * @endif
 */
extern "C" void ROS2TransportNamedInit(RTC::Manager* manager)
{
  openrtm_ros2::start_discovery(*manager);
  ROS2SerializerInit(manager);
}
