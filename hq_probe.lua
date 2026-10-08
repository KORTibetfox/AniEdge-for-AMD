local mp = require 'mp'
local utils = require 'mp.utils'
mp.register_event('video-reconfig', function()
    local p = mp.get_property_native('video-params', {})
    if not p.w or not p.h then return end
    mp.msg.info('HQ_SOURCE ' .. utils.format_json({width=p.w, height=p.h,
        fps=mp.get_property_number('container-fps',0), par=p.par or 1,
        rotate=p.rotate or 0, primaries=p.primaries, gamma=p.gamma,
        duration=mp.get_property_number('duration',0)}))
end)
