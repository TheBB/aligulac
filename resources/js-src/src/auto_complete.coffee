# ======================================================================
# AUTOCOMPLETE CACHE FUNCTIONS
# ======================================================================
save_autocomplete_object_to_cache = (obj) ->
    if autocomplete_ui_object.type != 'cache'
        save_result_to_cache key: autocomplete_ui_object.key, html: aligulacAutocompleteTemplates(autocomplete_ui_object), type: autocomplete_ui_object.type
    return
save_result_to_cache = (obj) ->
    if obj and window.localStorage
        recent_result = load_recent_results_from_cache()
        if (!recent_result) 
            recent_result = [];
        recent_result.shift
        recent_result.push html: obj.html, key: obj.key, type: 'cache', 'origin-type': "#{obj.type}s"
        window.localStorage.setItem 'aligulac.autocomplete.caching', JSON.stringify(recent_result)
        return
        
load_recent_results_from_cache = (restrict_to) ->
    result = []
    if window.localStorage
        result = JSON.parse localStorage.getItem 'aligulac.autocomplete.caching'
        if not items
            return []
        if not restrict_to
            return items
        for i in items
            for j in restrict_to
                if i['origin-type'] == j
                    result.push i;
    JSON.parse result
# ======================================================================
# AUTOCOMPLETE VARIA
# ======================================================================
aligulacAutocompleteTemplates = (obj) ->
    if obj.type == '--'
        obj.key = '-'
        return "<a>BYE</a>"

    if (obj.tag and obj.name and obj.fullname)
        return "<span class='autocomp-header'>#{autocomp_strings[obj.label]}</span>"

    switch obj.type
        when 'player'
            obj.key = "#{obj.tag} #{obj.id}"
            team = (
                if obj.teams and obj.teams.length > 0
                    "<span class='autocomp-team pull-right'>#{obj.teams[0][0]}</span>"
                else
                    ''
            )
            flag = (
                if obj.country
                    "<img src='#{flags_dir + obj.country.toLowerCase()}.png' />"
                else
                    ''
            )
            race = "<img src='#{races_dir + obj.race.toUpperCase()}.png' />"
            name = "<span>#{obj.tag}</span>"
            return "<a>#{flag}#{race}#{name}#{team}</a>"
        when 'team'
            obj.key = obj.name
            return "<a>#{obj.name}</a>"
        when 'event'
            obj.key = obj.fullname
            return "<a>#{obj.fullname}</a>"
        when 'cache'
            return obj.html
    "<a>#{ obj.value }</a>";
        
getResults = (term, restrict_to) ->
    if not restrict_to
        restrict_to = ['players', 'teams', 'events']
    else if typeof(restrict_to) == 'string'
        restrict_to = [restrict_to]
    deferred = $.Deferred()
    recent_results = load_recent_results_from_cache(restrict_to);
    if (((not term) or (term.length < 2)) and recent_results)
        return deferred.resolve cache: recent_results
    $.get('/search/json/', { q: term, search_for: restrict_to.join ','
    }).success (ajaxData) ->
        if recent_results
            ajaxData.cache = recent_results
        deferred.resolve ajaxData
    deferred

# ======================================================================
# AUTOCOMPLETE SEARCH BOX
# ======================================================================

init_search_box = () ->
    $searchbox = $('#search_box');
    $searchbox.bind 'focus', () -> $(this).autocomplete 'search'
    $searchbox.autocomplete(
        source: (request, response) ->
            $.when(getResults request.term).then (result) ->
                prepare_response = (list, type, label) ->
                    if not list or list.length == 0
                        return []
                    for x in list
                        x.type = type
                    [label: label].concat list
                playerresult = prepare_response result.players,
                    'player',
                    'Players'
                teamresult = prepare_response result.teams,
                    'team',
                    'Teams'
                eventresult = prepare_response result.events,
                    'event',
                    'Events'
                cacheresult = prepare_response result.cache,
                    'cache',
                    autocomp_strings['Your_recent_searches']
                response playerresult.concat teamresult.concat eventresult.concat cacheresult

        minLength: 0
        select: (event, ui) ->
            save_autocomplete_object_to_cache ui.item
            $searchbox.val(ui.item.key).closest('form').submit()
            false
        open: ->
            $('.ui-menu').width 'auto'
        ).data('ui-autocomplete')._renderItem = (ul, item) ->
            $('<li></li>')
                .append(aligulacAutocompleteTemplates item)
                .appendTo ul;

# ======================================================================
# AUTOCOMPLETE EVENT BOXES
# ======================================================================

init_event_boxes = () ->
    try
        $('.event-ac').autocomplete(
            source: (request, response) ->
                $.when(getResults(request.term, 'events')).then (result) ->

                    if not result? or not result.events? or result.events.length == 0
                        return []

                    for x in result.events
                        x.type = 'event'
                    response result.events

            minLength: 2
            select: (event, ui) ->
                $('.event-ac').val ui.item.key
                false
            open: ->
                $('.ui-menu').width 'auto'
        ).data('ui-autocomplete')._renderItem = (ul, item) ->
            $('<li></li>').append(aligulacAutocompleteTemplates item)
                          .appendTo ul;
# ======================================================================
# AUTOCOMPLETE PREDICTIONS
# ======================================================================

# Ugly hacking
add_extra_functions = () ->
    $.fn.getTags =  ->
        tagslist = $(this).val().split('\n')
        if tagslist[0] == ''
            tagslist = []
        tagslist

init_predictions = () ->
    idPlayersTextArea = $("#id_players")
    idPlayersTextArea.tagsInput
        autocomplete_opt:
            minLength: 0
            select: (event, ui) ->
                save_autocomplete_object_to_cache ui.item
                idPlayersTextArea.addTag ui.item.key
                $("#id_players_tag").focus();
                false
            open: ->
                $('.ui-menu').width 'auto'

        autocomplete_url: (request, response) ->
            $.when(getResults request.term, 'players').then (result) ->
                if result.players
                    for p in result.players
                        p.type = 'player'
                    if global_player_autocomplete_allow_byes and (request.term == 'bye' or request.term == '--')
                        result.players = [type: '--'].concat result.players
                else
                    result.players = []
                result.cache.unshift value: autocomp_strings['Your_recent_searches']
                response result.players.concat result.cache
        defaultText: autocomp_strings['Players']
        placeholderColor: '#9e9e9e'
        delimiter: '\n'
        width: '100%'
        formatAutocomplete: aligulacAutocompleteTemplates
        removeWithBackspace: true

    # Hacking the enter key down to submit the form when the
    # current input is empty
    # ... and the backspace, which works in the non-minified version of
    # jquery.tagsInput. We should switch away from it. It's a piece of crap.
    $('#id_players_addTag').keydown (event) ->
        if event.which == 13 and $('#id_players_tag').val() == ''
            $(this).closest("form").submit()
    $('#id_players_tag').keydown (event) ->
        if event.which == 8 and $(this).val() == ''
            event.preventDefault()
            id = $(this).attr('id').replace(/_tag$/, '')
            input = $("##{ id }")
            taglist = input.getTags()
            taglist.pop()
            input.importTags(taglist.join '\n')
            $(this).trigger('focus')

# Make sure the players input is styled like the rest of the form elements
init_other = () ->
    $('input#id_players_tag').focus ->
        $(this).parent().parent().css(
            'box-shadow',         'inset 0 1px 1px rgba(0,0,0,.075), 0 0 4px rgba(0,0,0,.4)'
        ).css(
            '-webkit-box-shadow', 'inset 0 1px 1px rgba(0,0,0,.075), 0 0 4px rgba(0,0,0,.4)'
        ).css('border-color', '#000000')
    .focusout ->
        $(this).parent().parent().css(
            'box-shadow',         'inset 0 1px 1px rgba(0,0,0,.075)'
        ).css(
            '-webkit-box-shadow', 'inset 0 1px 1px rgba(0,0,0,.075)'
        ).css('border-color', '#cccccc')

exports.AutoComplete = AutoComplete =
    init: () ->
        add_extra_functions()
        init_search_box()
        init_event_boxes()
        init_predictions()
        init_other()
