local mp = require 'mp'
local options = require 'mp.options'
local utils = require 'mp.utils'
local opts = {mode = 'light', auto = false}
options.read_options(opts, 'restore')
local directory = utils.join_path(mp.get_script_directory(), '../shaders')
local chains = {
    off = {},
    light = {'Anime4K_Clamp_Highlights.glsl', 'Anime4K_Upscale_Denoise_CNN_x2_M.glsl'},
    strong = {'Anime4K_Clamp_Highlights.glsl', 'Anime4K_Restore_CNN_M.glsl',
              'Anime4K_Upscale_Denoise_CNN_x2_M.glsl'}
}
local mode = chains[opts.mode] and opts.mode or 'light'
local previous = nil
local failures = 0
local grace_until = 0
local function apply(next_mode, reason)
    mode = next_mode
    local files = {}
    for _, name in ipairs(chains[mode]) do
        table.insert(files, utils.join_path(directory, name))
    end
    mp.set_property_native('glsl-shaders', files)
    mp.msg.info('Restoration mode: ' .. mode .. '; automatic=' .. tostring(opts.auto))
    mp.osd_message('Anime restore: ' .. mode .. (reason or '') .. '\n1 original | 2 light | 3 strong | 4 auto', 4)
    previous = nil
    failures = 0
    grace_until = mp.get_time() + 5
end
mp.add_key_binding('1', 'restore-original', function() apply('off') end)
mp.add_key_binding('2', 'restore-light', function() apply('light') end)
mp.add_key_binding('3', 'restore-strong', function() apply('strong') end)
mp.add_key_binding('4', 'restore-auto', function()
    opts.auto = not opts.auto
    previous = nil
    failures = 0
    mp.osd_message('Automatic restoration adjustment: ' .. tostring(opts.auto), 3)
end)
mp.register_event('file-loaded', function() apply(mode) end)
mp.register_event('seek', function()
    previous = nil
    failures = 0
    grace_until = mp.get_time() + 5
end)
mp.register_event('shutdown', function()
    mp.msg.info('Playback summary: mode=' .. mode ..
                '; renderer_drops=' .. mp.get_property_number('frame-drop-count', 0) ..
                '; decoder_drops=' .. mp.get_property_number('decoder-frame-drop-count', 0))
end)
-- Conservative fallback: two consecutive three-second samples with >2 rendered drops.
-- This is a heuristic, not evidence that the shader caused the drops.
mp.add_periodic_timer(3, function()
    local drops = mp.get_property_number('frame-drop-count', 0)
    if mp.get_property_bool('pause') or mp.get_property_bool('seeking') or mp.get_time() < grace_until then
        previous = nil
        failures = 0
        return
    end
    if previous and drops >= previous and drops - previous > 2 then failures = failures + 1
    else failures = 0 end
    previous = drops
    if opts.auto and failures >= 2 and mode ~= 'off' then
        apply(mode == 'strong' and 'light' or 'off', ' (frame-drop fallback)')
    end
end)
