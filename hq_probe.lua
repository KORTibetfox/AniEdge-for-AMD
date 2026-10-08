local mp = require 'mp'
local utils = require 'mp.utils'
local snapshot = nil
local function capture()
    local p = mp.get_property_native('video-params', {})
    if not p.w or not p.h then return end
    local fps = mp.get_property_number('container-fps',0)
    local fps_source = 'container-fps'
    if fps <= 0 then
        fps = mp.get_property_number('current-tracks/video/demux-fps',0)
        fps_source = 'track-demux-fps'
    end
    if fps <= 0 then
        fps = mp.get_property_number('estimated-vf-fps',0)
        fps_source = 'estimated-vf-fps'
    end
    -- mpv can send video-reconfig again while unloading, after FPS/duration reset.
    -- Preserve the valid decoded snapshot rather than replacing it with zeros.
    if fps <= 0 then return end
    if snapshot and snapshot.pixelformat and not p.pixelformat then return end
    snapshot = {width=p.w, height=p.h, pixelformat=p.pixelformat,
        fps=fps, fps_source=fps_source, par=p.par or 1,
        rotate=p.rotate or 0, primaries=p.primaries, gamma=p.gamma,
        duration=mp.get_property_number('duration',0)}
end
mp.register_event('file-loaded', capture)
mp.register_event('video-reconfig', capture)
mp.register_event('shutdown', function()
    if snapshot then mp.msg.info('HQ_SOURCE ' .. utils.format_json(snapshot)) end
end)
