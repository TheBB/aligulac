exports.Aligulac = Aligulac =
    init: () ->
        AutoComplete = require('auto_complete').AutoComplete
        Common       = require('common').Common
        GenShort     = require('genshort').GenShort
        Menu         = require('menu').Menu

        Menu.init()
        AutoComplete.init()
        Common.init()
        GenShort.init()

    init_extra: (apps) ->
        apps_list = apps.split " "
        if 'eventmgr' in apps_list
            EventMgr = require('eventmgr').EventMgr
            EventMgr.init()
        if 'eventres' in apps_list
            EventRes = require('eventres').EventRes
            EventRes.init()
        if 'clocks' in apps_list
            Clocks = require('clocks').Clocks
            Clocks.init()
        if 'player_info' in apps_list
            PlayerInfo = require('player_info').PlayerInfo
            PlayerInfo.init()
