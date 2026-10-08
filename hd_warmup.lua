local mp = require 'mp'
local preparing = false
local was_paused = false
mp.add_hook('on_load',50,function()
    was_paused=mp.get_property_bool('pause',false)
    preparing=true
    mp.set_property_bool('pause',true)
end)
mp.register_event('playback-restart',function()
    if not preparing then return end
    preparing=false
    mp.add_timeout(0.1,function()
        if not was_paused then mp.set_property_bool('pause',false) end
    end)
end)
