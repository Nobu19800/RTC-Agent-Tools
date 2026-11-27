#include "Control.hpp"
#include "Pdu.hpp"

#include <rtm/idl/BasicDataTypeSkel.h>
#include <rtm/DataFlowComponentBase.h>
#include <rtm/DataInPort.h>
#include <rtm/Manager.h>
#include <hako_asset.h>
#include <geometry_msgs/pdu_ctype_Twist.h>
#include <hako_msgs/pdu_ctype_HakoDroneCmdTakeoff.h>
#include <hako_msgs/pdu_ctype_HakoDroneCmdMove.h>
#include <hako_msgs/pdu_ctype_HakoDroneCmdLand.h>

#include <chrono>
#include <filesystem>
#include <fstream>
#include <string>

namespace {
using Clock = std::chrono::steady_clock;

template<class Value, std::size_t Capacity>
std::optional<Value> read_pdu(int channel)
{
  drone::Payload<Value, Capacity> payload{};
  if (hako_asset_pdu_read("Drone", channel, payload.data(), payload.size()) != 0) {
    return std::nullopt;
  }
  return drone::decode<Value>(payload);
}

template<class Value, std::size_t Capacity>
bool write_request(int channel, Value value)
{
  value.header.request = 1;
  const auto payload = drone::encode<Value, Capacity>(value);
  return hako_asset_pdu_write("Drone", channel, payload.data(), payload.size()) == 0;
}

class Adapter final : public RTC::DataFlowComponentBase {
 public:
  explicit Adapter(RTC::Manager* manager)
      : RTC::DataFlowComponentBase(manager), joystick_("joystick", input_) {}

  RTC::ReturnCode_t onInitialize() override
  {
    return addInPort("joystick", joystick_) ? RTC::RTC_OK : RTC::RTC_ERROR;
  }

  RTC::ReturnCode_t onActivated(RTC::UniqueId) override
  {
    pending_ = 0;
    airborne_ = false;
    input_time_.reset();
    return hako_initialize_for_external() == 0 ? RTC::RTC_OK : RTC::RTC_ERROR;
  }

  RTC::ReturnCode_t onExecute(RTC::UniqueId) override
  {
    const auto now = Clock::now();
    if (joystick_.isNew() && joystick_.read()) {
      if (input_.data.length() == 2) {
        axes_ = {input_.data[0], input_.data[1]};
        input_time_ = now;
      } else {
        input_time_.reset();
      }
    }
    if (pending_ != 0) {
      return poll_response(now);
    }
    const auto pose = read_pdu<Hako_Twist, 72>(1);
    if (!pose) {
      return RTC::RTC_OK;
    }
    const auto action = read_action();
    if (action == "takeoff" && !airborne_) {
      Hako_HakoDroneCmdTakeoff cmd{};
      cmd.height = 1.0;
      cmd.speed = 0.5;
      return send<Hako_HakoDroneCmdTakeoff, 88>(6, cmd, now);
    }
    if (action == "land" && airborne_) {
      Hako_HakoDroneCmdLand cmd{};
      cmd.speed = 0.5;
      return send<Hako_HakoDroneCmdLand, 88>(8, cmd, now);
    }
    if (input_time_) {
      const auto age = std::chrono::duration<double>(now - *input_time_).count();
      const auto move = drone::move_target(
          axes_[0], axes_[1], {pose->linear.x, pose->linear.y}, age, airborne_);
      if (move) {
        Hako_HakoDroneCmdMove cmd{};
        cmd.x = move->x;
        cmd.y = move->y;
        cmd.z = move->z;
        cmd.speed = move->speed;
        return send<Hako_HakoDroneCmdMove, 104>(7, cmd, now);
      }
    }
    return RTC::RTC_OK;
  }

 private:
  static std::string read_action()
  {
    const auto path = std::filesystem::path("action.request");
    std::ifstream file(path);
    std::string action;
    if (file >> action) {
      file.close();
      std::filesystem::remove(path);
    }
    return action;
  }

  template<class Value, std::size_t Capacity>
  RTC::ReturnCode_t send(int channel, const Value& value, Clock::time_point now)
  {
    if (!write_request<Value, Capacity>(channel, value)) {
      return RTC::RTC_ERROR;
    }
    pending_ = channel;
    request_time_ = now;
    return RTC::RTC_OK;
  }

  template<class Value, std::size_t Capacity>
  std::optional<Hako_HakoDroneCmdHeader> read_header() const
  {
    const auto value = read_pdu<Value, Capacity>(pending_);
    return value ? std::optional{value->header} : std::nullopt;
  }

  RTC::ReturnCode_t poll_response(Clock::time_point now)
  {
    std::optional<Hako_HakoDroneCmdHeader> header;
    switch (pending_) {
      case 6: header = read_header<Hako_HakoDroneCmdTakeoff, 88>(); break;
      case 7: header = read_header<Hako_HakoDroneCmdMove, 104>(); break;
      case 8: header = read_header<Hako_HakoDroneCmdLand, 88>(); break;
      default: return RTC::RTC_ERROR;
    }
    const auto elapsed = std::chrono::duration<double>(now - request_time_).count();
    const auto result = drone::response(
        header && header->request, header && header->result,
        header ? header->result_code : 0, elapsed);
    if (result == drone::Response::rejected || result == drone::Response::timed_out) {
      return RTC::RTC_ERROR;
    }
    if (result == drone::Response::accepted) {
      if (pending_ != 7) {
        airborne_ = pending_ == 6;
      }
      pending_ = 0;
    }
    return RTC::RTC_OK;
  }

  RTC::TimedFloatSeq input_{};
  RTC::InPort<RTC::TimedFloatSeq> joystick_;
  std::array<double, 2> axes_{};
  std::optional<Clock::time_point> input_time_;
  Clock::time_point request_time_{};
  int pending_{};
  bool airborne_{};
};

void register_adapter(RTC::Manager* manager)
{
  const char* spec[] = {
      "implementation_id", "DroneJoystickAdapterCpp",
      "type_name", "DroneJoystickAdapterCpp",
      "category", "example",
      "max_instance", "1",
      "language", "C++",
      ""};
  coil::Properties properties(spec);
  manager->registerFactory(properties, RTC::Create<Adapter>, RTC::Delete<Adapter>);
  manager->createComponent("DroneJoystickAdapterCpp");
}
}

int main(int argc, char** argv)
{
  auto* manager = RTC::Manager::init(argc, argv);
  manager->setModuleInitProc(register_adapter);
  manager->activateManager();
  manager->runManager();
}
