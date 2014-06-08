/* ======================================================================
 * MAIN MENU ACCESSIBILITY
 * ======================================================================
 */

function toggle_navbar_method() {
    // Only enable hovering on click devices.
    if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent) ||
            $(window).width() <= 768) {
        $('.navbar .dropdown').off('mouseover').off('mouseout');
    } else {
        $('.navbar .dropdown').on('mouseover', function () {
            $('.dropdown-toggle', this).trigger('click');
        }).on('mouseout', function () {
            $('.dropdown-toggle', this).trigger('click').blur();
        });
    }
}
toggle_navbar_method();
//$(window).resize(toggle_navbar_method);


/* ======================================================================
 * SHORT URL GENERATION
 * ======================================================================
 */

function gen_short(uri) {
    var http = new XMLHttpRequest();
    http.open("GET", "/m/new/?url=" + encodeURIComponent(uri, false));

    http.onreadystatechange = function () {
        if (http.readyState == 4 && http.status == 200) {
            $('#gen_short').hide();
            $('#disp_short').html('<a href="/m/' + http.responseText + '/">/m/' + http.responseText + '</a>');
        }
    };

    http.send(null);
}

/* ======================================================================
 * AUTOCOMPLETE SEARCH TEXTBOX
 * ======================================================================
 */

var autocomp_templates = function (object) {
    if (!object.tag && !object.name && !object.fullname)
        return '<span class="autocomp-header">' + autocomp_strings[object.label] + '</span>';
    switch (object.type) {
        case 'player':
        object.key = object.tag + ' ' + object.id;
        var team = '';
        if (object.teams && object.teams.length > 0) {
            team = object.teams[0][0];
            team = '<span class="autocomp-team pull-right">' + team + '</span>';
        }
        return '<a>{flag}<img src="{race}"><span class="autocomp-player">{name}</span>{team}</a>'
               .replace('{flag}', object.country ?
                    '<img src="' + flags_dir + object.country.toLowerCase() + '.png">' :
                    '<img src="' + races_dir + 'trans.png">')
               .replace('{race}', races_dir + object.race.toUpperCase() + '.png')
               .replace('{name}', object.tag)
               .replace('{team}', team);

        case 'team':
        object.key = object.name;
        return '<a>{name}</a>'.replace('{name}', object.name);

        case 'event':
        object.key = object.fullname;
        return '<a>{name}</a>'.replace('{name}', object.fullname);
    }
    return '<a>' + object.value + '</a>';
}

var get_results = function (term, restrict_to) {
    if (!restrict_to)
        restrict_to = ['players', 'teams', 'events'];

    if (typeof(restrict_to) == 'string')
        restrict_to = [restrict_to];

    var deferred = $.Deferred();
    var url = '/search/json/';
    $.ajax({
        type: 'GET',
        url: url,
        dataType: 'json',
        data: { q: term, search_for: restrict_to.join(',') }
    }).success(function (data) {
        deferred.resolve(data);
    });

    return deferred;
};

$(document).ready(function () {
    $("#search_box").autocomplete({
        source: function (request, response) {
            $.when(get_results(request.term)).then(function (result) {
                var player_res = [];
                var team_res = [];
                var event_res = [];

                if (result.players != undefined && result.players.length > 0) {
                    player_res = [{ label: 'Players' }].concat(result.players);
                    for (var i = 1; i < player_res.length; i++)
                        player_res[i].type = 'player';
                }

                if (result.teams != undefined && result.teams.length > 0) {
                    team_res = [{ label: 'Teams' }].concat(result.teams);
                    for (var i = 1; i < team_res.length; i++)
                        team_res[i].type = 'team';
                }

                if (result.events != undefined && result.events.length > 0) {
                    event_res = [{ label: 'Events' }].concat(result.events);
                    for (var i = 1; i < event_res.length; i++)
                        event_res[i].type = 'event';
                }

                var data = player_res.concat(team_res.concat(event_res));
                response(data);
            }); 
        },
        minLength: 2,
        position: { my: "right top", at: "right bottom", collision: "none" },
        select: function (event, ui) {
            $('#search_box').val(ui.item.key)
                            .closest('form')
                            .submit();
            return false;
        },
        open: function () {
            $('.ui-menu').width('auto');
        }
    }).data('ui-autocomplete')._renderItem = function (ul, item) {
        return $('<li></li>').append(autocomp_templates(item))
                             .appendTo(ul);
    };
});
