local mp = require 'mp'
local utils = require 'mp.utils'
local options = require 'mp.options'
local opts = {output=''}
options.read_options(opts,'metrics')
local report = {samples=0, max_abs_avsync=0, renderer_drops=0, decoder_drops=0, drop_events={}}
local function sample()
    local drops=mp.get_property_number('frame-drop-count',0)
    if drops and drops > report.renderer_drops then
        table.insert(report.drop_events,{time=mp.get_property_number('time-pos',0),count=drops})
    end
    report.renderer_drops = math.max(report.renderer_drops,(drops or 0))
    report.decoder_drops = math.max(report.decoder_drops,(mp.get_property_number('decoder-frame-drop-count',0)))
    local sync = mp.get_property_number('avsync')
    if sync and not mp.get_property_bool('eof-reached') and not mp.get_property_bool('pause') then report.max_abs_avsync=math.max(report.max_abs_avsync,math.abs(sync)) end
    report.samples=report.samples+1
    local dims=mp.get_property_native('osd-dimensions')
    if dims then report.output_dimensions=dims end
    local params=mp.get_property_native('video-params')
    if params then report.video=params end
    local passes=mp.get_property_native('vo-passes')
    if passes then report.gpu_passes=passes end
    local hwdec=mp.get_property('hwdec-current')
    if hwdec then report.hwdec=hwdec end
end
mp.add_periodic_timer(0.5,sample)
mp.register_event('shutdown',function()
    sample()
    if opts.output ~= '' then
        local file=io.open(opts.output,'w')
        if file then file:write(utils.format_json(report));file:close() end
    end
    mp.msg.info('Playback metrics: drops='..report.renderer_drops..'; max_abs_avsync='..report.max_abs_avsync)
end)
