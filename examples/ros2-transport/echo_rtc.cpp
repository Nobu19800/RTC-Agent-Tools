#include <rtm/idl/BasicDataTypeSkel.h>
#include <rtm/DataFlowComponentBase.h>
#include <rtm/DataInPort.h>
#include <rtm/DataOutPort.h>
#include <rtm/Manager.h>

#include <string>

class Echo final : public RTC::DataFlowComponentBase
{
public:
  explicit Echo(RTC::Manager* manager)
    : RTC::DataFlowComponentBase(manager),
      input_port_("input", input_), output_port_("output", output_)
  {
  }

  RTC::ReturnCode_t onInitialize() override
  {
    addInPort("input", input_port_);
    addOutPort("output", output_port_);
    return RTC::RTC_OK;
  }

  RTC::ReturnCode_t onExecute(RTC::UniqueId) override
  {
    if (input_port_.isNew() && input_port_.read()) {
      const std::string message = std::string("rtc-echo:") + input_.data.in();
      output_.data = message.c_str();
      output_port_.write();
    }
    return RTC::RTC_OK;
  }

private:
  RTC::TimedString input_{};
  RTC::TimedString output_{};
  RTC::InPort<RTC::TimedString> input_port_;
  RTC::OutPort<RTC::TimedString> output_port_;
};

void register_echo(RTC::Manager* manager)
{
  const char* profile[] = {
    "implementation_id", "RtsdEcho",
    "type_name", "RtsdEcho",
    "description", "ROS2Transport round-trip test",
    "version", "1.0",
    "vendor", "RTC-Agent-Tools",
    "category", "example",
    "activity_type", "PERIODIC",
    "component_type", "DataFlowComponent",
    "max_instance", "1",
    "language", "C++",
    "lang_type", "compile",
    "",
  };
  coil::Properties properties(profile);
  manager->registerFactory(properties, RTC::Create<Echo>, RTC::Delete<Echo>);
  manager->createComponent("RtsdEcho");
}

int main(int argc, char** argv)
{
  RTC::Manager* manager = RTC::Manager::init(argc, argv);
  manager->setModuleInitProc(register_echo);
  manager->activateManager();
  manager->runManager();
}
