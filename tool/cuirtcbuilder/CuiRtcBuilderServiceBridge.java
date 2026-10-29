// Compatibility bridge for the bundled RTC Builder profile loader.
// It restores the IDL file path which ParamUtil currently loads only as a
// display value, then delegates template generation to the original libraries.
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.lang.reflect.Method;
import java.util.*;
import jp.go.aist.rtm.rtcbuilder.Generator;
import jp.go.aist.rtm.rtcbuilder.generator.*;
import jp.go.aist.rtm.rtcbuilder.generator.param.*;
import jp.go.aist.rtm.rtcbuilder.generator.param.idl.*;

class CuiRtcBuilderServiceBridge {
    public static void main(String[] args) throws Exception {
        Path output = Paths.get(args[0]).toAbsolutePath();
        ProfileHandler handler = new ProfileHandler(true);
        handler.addManager(new jp.go.aist.rtm.rtcbuilder.java.manager.JavaCMakeGenerateManager());
        handler.addManager(new jp.go.aist.rtm.rtcbuilder.java.manager.JavaGenerateManager());
        handler.addManager(new jp.go.aist.rtm.rtcbuilder.python.manager.PythonCMakeGenerateManager());
        handler.addManager(new jp.go.aist.rtm.rtcbuilder.python.manager.PythonGenerateManager());
        handler.addManager(new jp.go.aist.rtm.rtcbuilder.processing.manager.ProcessingCMakeGenerateManager());
        handler.addManager(new jp.go.aist.rtm.rtcbuilder.processing.manager.ProcessingGenerateManager());
        handler.addManager(new jp.go.aist.rtm.rtcbuilder.lua.manager.LuaCMakeGenerateManager());
        handler.addManager(new jp.go.aist.rtm.rtcbuilder.lua.manager.LuaGenerateManager());
        GeneratorParam params = handler.restorefromXMLFile(args[1], true);
        RtcParam rtc = params.getRtcParam();
        List<IdlPathParam> search = new ArrayList<>();
        for (int i = 2; i < args.length; i++) search.add(new IdlPathParam(args[i], false));
        for (ServicePortParam port : rtc.getServicePorts()) {
            for (ServicePortInterfaceParam iface : port.getServicePortInterfaces()) {
                String reference = iface.getIdlDispFile();
                if (reference == null || reference.isEmpty())
                    throw new IllegalArgumentException("Missing IDL for " + iface.getInterfaceType());
                Path path = Paths.get(reference).toAbsolutePath().normalize();
                if (!Files.isRegularFile(path)) throw new IllegalArgumentException("IDL not found: " + path);
                iface.setIdlFile(path.toString());
                search.add(new IdlPathParam(path.getParent().toString(), false));
            }
        }
        // Reuse the bundled CLI's type extraction, including standard RTM IDLs.
        Class<?> cli = Class.forName("jp.go.aist.rtm.cuirtcbuilder.CuiRtcBuilder");
        Method extract = cli.getDeclaredMethod("extractDataTypes", List.class, GeneratorParam.class);
        extract.setAccessible(true);
        extract.invoke(null, search, params);
        Generator generator = new Generator();
        generator.addGenerateManager(new jp.go.aist.rtm.rtcbuilder.java.manager.JavaCMakeGenerateManager());
        generator.addGenerateManager(new jp.go.aist.rtm.rtcbuilder.java.manager.JavaGenerateManager());
        generator.addGenerateManager(new jp.go.aist.rtm.rtcbuilder.python.manager.PythonCMakeGenerateManager());
        generator.addGenerateManager(new jp.go.aist.rtm.rtcbuilder.python.manager.PythonGenerateManager());
        generator.addGenerateManager(new jp.go.aist.rtm.rtcbuilder.processing.manager.ProcessingCMakeGenerateManager());
        generator.addGenerateManager(new jp.go.aist.rtm.rtcbuilder.processing.manager.ProcessingGenerateManager());
        generator.addGenerateManager(new jp.go.aist.rtm.rtcbuilder.lua.manager.LuaCMakeGenerateManager());
        generator.addGenerateManager(new jp.go.aist.rtm.rtcbuilder.lua.manager.LuaGenerateManager());
        generator.validate(rtc);
        List<GeneratedResult> results = generator.generateTemplateCode(params, search);
        for (GeneratedResult result : results) {
            if (result.getName() == null || result.getName().isEmpty()) continue;
            Path target = output.resolve(result.getName()).normalize();
            if (!target.startsWith(output)) throw new IllegalArgumentException("Output escapes folder: " + target);
            Files.createDirectories(target.getParent());
            Files.writeString(target, result.getCode(), StandardCharsets.UTF_8);
        }
        for (IdlFileParam idl : rtc.getProviderIdlPathes()) copyIdl(output, Paths.get(idl.getIdlPath()));
        for (IdlFileParam idl : rtc.getConsumerIdlPathes()) copyIdl(output, Paths.get(idl.getIdlPath()));
        for (String idl : rtc.getIncludedIdls()) copyIdl(output, Paths.get(idl));
    }
    private static void copyIdl(Path output, Path source) throws Exception {
        Path target = output.resolve("idl").resolve(source.getFileName());
        Files.createDirectories(target.getParent());
        if (!source.toAbsolutePath().normalize().equals(target.toAbsolutePath().normalize()))
            Files.copy(source, target, StandardCopyOption.REPLACE_EXISTING);
    }
}
