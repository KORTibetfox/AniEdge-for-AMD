local mp = require 'mp'
local max_avsync = 0
local avsync_samples = 0
mp.add_periodic_timer(0.5,function()
    local value = mp.get_property_number('avsync')
    if value and not mp.get_property_bool('pause') and not mp.get_property_bool('eof-reached') then
        max_avsync = math.max(max_avsync,math.abs(value))
        avsync_samples = avsync_samples + 1
    end
end)
mp.register_event('file-loaded',function()
    mp.osd_message('HQ: Real-CUGAN Pro 2x / DirectML\nSequential playback · seeking unavailable',5)
end)
for _, key in ipairs({'LEFT','RIGHT','UP','DOWN','PGUP','PGDWN','1','2','3','4'}) do
    mp.add_forced_key_binding(key,'hq-block-'..key,function()
        mp.osd_message('HQ prototype: sequential playback only',3)
    end)
end
mp.register_event('shutdown',function()
    mp.msg.info('HQ playback summary: renderer_drops='..mp.get_property_number('frame-drop-count',0)..
        '; decoder_drops='..mp.get_property_number('decoder-frame-drop-count',0)..
        '; max_abs_avsync='..max_avsync..'; avsync_samples='..avsync_samples)
end)
