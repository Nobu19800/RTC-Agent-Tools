# RTSystemDesigner Module Settings

[日本語](../designer-module-settings.md)

Click a module on the canvas to open its settings. Available fields depend on **Module Kind**. Deployment settings describe the target environment for the agent to prepare and use.

## Common settings

| Tab | What to set |
| --- | --- |
| General | Module Name identifies the implementation, Instance Name identifies the instance, and Module Kind selects RTC, Hakoniwa Asset, or ROS 2 Node. State is read-only. |
| Deployment | Host is the deployment target. Executable, Working Directory, Arguments, and Environment describe how to launch it. For ROS 2, set executable in General. |
| Configuration | Set Parameter Name and Default Value for RTCs, or Parameter Value for other modules. Set the ROS 2 parameter file in General. |
| Ports | Set port names, directions, and fully qualified types to match the intended endpoints. Choose a listed type or enter the required type. |
| Implementation | Use Summary for the role, Requirements for behavior and mappings, Constraints for restrictions, and Notes for context and unresolved items. |

## RTC

| Tab or section | What to set |
| --- | --- |
| General → Basic Profile | Set the module description and identity, instance limit, execution rate, RTC and component types, activity type, execution context, generation language, and Choreonoid option. |
| General → rtc.conf | CORBA Name Servers sets the runtime naming service. manager.shutdown_auto controls automatic manager shutdown. |
| Activity | Choose Generate for each callback and describe its behavior, preconditions, and postconditions. By default, onInitialize is ON and the others are OFF. Explicit values take precedence. |
| FSM | Enable FSM, choose StaticFSM or DynamicFSM, set the event port and variable, and create, import, or edit SCXML. The event list displays transitions. |
| Documentation | Record the overview, inputs and outputs, algorithm, references, contact details, and license. |
| Container | Describe target OS, workspace, language, configuration, functional modules, libraries, and repository URLs and branches. |
| RTC.xml | Inspect and edit the RTC profile XML. Disconnect affected ports before deleting or renaming them. |

Under **Ports**, add an InPort, OutPort, or ServicePort. For DataPorts, set the RTC type and relevant profile documentation, such as meaning and unit. For a ServicePort, set the interface name, IDL type, and Consumer or Provider role. The IDL list includes OpenRTM-aist definitions. Under **Configuration**, set the type, variable, unit, constraints, and widget. Step is available for slider and spin widgets.

## ROS 2 Node

In **General → ROS 2**, set `package`, `executable`, `namespace`, and `parametersFile`. Record launch arguments and environment under **Deployment**. In **Ports**, record topic direction and message type, or choose Service or Action and configure the name, type, and client/server roles. Resolve fully qualified names with the namespace. For RTC–ROS 2 edges, record the type mapping, topic, and transport settings. [RTC–ROS 2 integration](rtc-ros2.md)

## Hakoniwa Asset

Use the selected asset profile to check each PDU port's name, direction, data type, and **Channel ID**. In **Implementation → Requirements**, record the robot name, PDU name, capacity, layout, and transfer requirements used by the approved configuration. For RTC–Hakoniwa edges, specify the serializer and mapping. [RTC–Hakoniwa asset integration](rtc-hakoniwa.md)

[Start from an empty session](empty-session.md)
