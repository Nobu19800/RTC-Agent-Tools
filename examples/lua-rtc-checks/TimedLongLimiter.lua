local openrtm = require "openrtm"
local limit = require "limit"

local spec = {
    implementation_id = "TimedLongLimiter",
    type_name = "TimedLongLimiter",
    description = "Clamp a TimedLong sample to [-100, 100]",
    version = "1.0",
    vendor = "RTC-Agent-Tools",
    category = "example",
    activity_type = "DataFlowComponent",
    max_instance = "1",
    language = "Lua",
    lang_type = "script",
}

local function create(manager)
    local rtc = setmetatable({}, {__index = openrtm.RTObject.new(manager)})
    local data_type = "::RTC::TimedLong"
    local input_data = openrtm.RTCUtil.instantiateDataType(data_type)
    local output_data = openrtm.RTCUtil.instantiateDataType(data_type)
    local input = openrtm.InPort.new("in", input_data, data_type)
    local output = openrtm.OutPort.new("out", output_data, data_type)

    function rtc:onInitialize()
        self:addInPort("in", input)
        self:addOutPort("out", output)
        return self._ReturnCode_t.RTC_OK
    end

    function rtc:onExecute()
        if input:isNew() then
            local sample = input:read()
            output_data.data = limit.apply(sample.data)
            output_data.tm.sec = sample.tm.sec
            output_data.tm.nsec = sample.tm.nsec
            output:write()
        end
        return self._ReturnCode_t.RTC_OK
    end

    return rtc
end

local manager = openrtm.Manager
manager:init(arg)
manager:setModuleInitProc(function(mgr)
    local profile = openrtm.Properties.new({defaults_map = spec})
    mgr:registerFactory(profile, create, openrtm.Factory.Delete)
    assert(mgr:createComponent("TimedLongLimiter"), "RTC creation failed")
end)
manager:activateManager()
manager:runManager()
