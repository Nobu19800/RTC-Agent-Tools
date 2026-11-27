local limit = {}

function limit.apply(value)
    if value < -100 then
        return -100
    end
    if value > 100 then
        return 100
    end
    return value
end

return limit
