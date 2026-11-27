local luaunit = require "luaunit"
local limit = require "limit"

local function test_lower_saturation()
    luaunit.assertEquals(limit.apply(-2147483648), -100)
end

local function test_upper_saturation()
    luaunit.assertEquals(limit.apply(2147483647), 100)
end

local function test_boundaries_and_passthrough()
    for _, value in ipairs({-100, -25, 0, 25, 100}) do
        luaunit.assertEquals(limit.apply(value), value)
    end
end

os.exit(luaunit.LuaUnit:new():runSuiteByInstances({
    {"test_lower_saturation", test_lower_saturation},
    {"test_upper_saturation", test_upper_saturation},
    {"test_boundaries_and_passthrough", test_boundaries_and_passthrough},
}))
