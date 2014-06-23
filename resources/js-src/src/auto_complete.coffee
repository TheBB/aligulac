# ======================================================================
# AUTOCOMPLETE VARIA
# ======================================================================

aligulacAutocompleteTemplates = (obj) ->
    if not (obj.tag? || obj.name? || obj.fullname?)
        return "<span class='autocomp-header'>#{ autocomp_strings[obj.label] }</span>"

    switch obj.type
        when 'player'
            obj.key = obj.tag + ' ' + obj.id
            team = (
                if obj.teams? && obj.teams.length > 0
                    "<span class='autocomp-team pull-right'>#{ obj.teams[0][0] }</span>"
                else
                    ''
            )
            flag = (
                if obj.country?
                    "<img src='#{ flags_dir + obj.country.toLowerCase() }.png' />"
                else
                    ''
            )
            race = "<img src='#{ races_dir + obj.race.toUpperCase() }.png' />"
            name = "<span>#{ obj.tag }</span>"
            return "<a>#{ flag }#{ race }#{ name }#{ team }</a>"
        when 'team'
            obj.key = obj.name
            return "<a>#{ obj.name }</a>"
        when 'event'
            obj.key = obj.fullname
            return "<a>#{ obj.fullname }</a>"

    "<a>#{ obj.value }</a>";

getResults = (term, restrict_to) ->

    if not restrict_to?
        restrict_to = ['players', 'teams', 'events']
    else if typeof(restrict_to) == 'string'
        restrict_to = [restrict_to]

    deferred = $.Deferred()
    url = '/search/json/'
    $.ajax({
        type: 'GET'
        url: url
        dataType: 'json'
        data: q: term, search_for: restrict_to.join ','
    }).success (ajaxData) ->
        deferred.resolve ajaxData

    deferred

# ======================================================================
# AUTOCOMPLETE SEARCH BOX
# ======================================================================

$(document).ready ->
    $('#search_box').autocomplete(
        source: (request, response) ->
            $.when(getResults request.term).then (result) ->

                prepare_response = (list, type, label) ->
                    if not list? or list.length == 0
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

                response playerresult.concat teamresult.concat eventresult

        minLength: 2
        select: (event, ui) ->
            $('#search_box').val ui.item.key
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

$(document).ready ->
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

$(document).ready ->
    idPlayersTextArea = $("#id_players")
    idPlayersTextArea.tagsInput
        autocomplete_opt:
            minLength: 2
            select: (event, ui) ->
                $idPlayersTextArea.addTag ui.item.key
                $("#id_players_tag").focus();
                false
            open: ->
                $('.ui-menu').width 'auto'

        autocomplete_url: (request, response) ->
            $.when(getResults request.term, 'players').then (result) ->
                if result.players?
                    for p in result.players
                        p.type = 'player'

                    response result.players
        defaultText: autocomp_strings['Players']
        placeholderColor: '#9e9e9e'
        delimiter: '\n'
        width: '100%'
        formatAutocomplete: aligulacAutocompleteTemplates

    # Hacking the enter key down to submit the form when the
    # current input is empty
    $("#id_players_addTag").keydown (event) ->
        if event.which == 13 and $("#id_players_tag").val() == ""
            $(this).closest("form").submit()

# Make sure the players input is styled like the rest of the form elements
$(document).ready ->
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
