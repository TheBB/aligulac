/* ======================================================================
 * GENERAL STUFF
 * ======================================================================
 */

/* Checks for element relationship
 */
function is_descendant(par, child)
{
    var node = child;
    while (node != null) 
    {
        if (node == par)
            return true;
        node = node.parentNode;
    }
    return false;
}

/* Trims whitespace
 */
function trim(s)
{
    return s.replace(/^\s\s*/, '').replace(/\s\s*$/, '');
}

/* Sets the content of a textbox
 */
function set_textbox(id, s)
{
    document.getElementById(id).value = s;
}

/* Sets a line of a textarea
 */
function set_textarea_line(id, s, line)
{
    var cur = document.getElementById(id).value;
    cur = cur.replace(/\r\n/, '\n');
    var a = cur.split('\n');
    a[line] = s;
    document.getElementById(id).value = a.join('\n');
}

/* ======================================================================
 * VISIBILITY TOGGLING
 * ======================================================================
 */

/* Toggles the display style property of the element given by ID between none and whatever is given in the
 * visible argument
 */
function togvis(id, visible)
{
    var d = document.getElementById(id);
    if (d.style.display == 'none')
        d.style.display = visible;
    else
        d.style.display = 'none';
}

/* Toggles visibility of tbody elements.
 */
function togvis_tbody(id)
{
    togvis(id, 'table-row-group');
}

/* Toggles visibility of div elements.
 */
function togvis_div(id)
{
    togvis(id, 'block');
}

/* Toggles visibility of span elements.
 */
function togvis_span(id)
{
    togvis(id, 'inline');
}

/* Makes all elements given in the all array invisible except for the one given by id
 */
function switch_to(id, all)
{
    for (var i = 0; i < all.length; i++)
    {
        if (all[i] == id)
            document.getElementById(all[i]).style.display = 'block';
        else
            document.getElementById(all[i]).style.display = 'none';
    }
}

function switch_tab(id, all)
{
    for (var i = 0; i < all.length; i++)
    {
        if (all[i] == id)
        {
            document.getElementById(all[i]).style.display = 'table-row-group';
            document.getElementById(all[i] + '-tab').className = 'tabsel';
        }
        else
        {
            document.getElementById(all[i]).style.display = 'none';
            document.getElementById(all[i] + '-tab').className = 'tabunsel';
        }
    }
}

/* Toggles a popup form.
 */
function toggle_form(id)
{
    var element = document.getElementById(id);
    element.style.display = 'block';
}

/* Hides charts in a player page. Sometimes necessary for popup forms to look OK.
 */
function hide_charts()
{
    if (document.getElementById('chart'))
        document.getElementById('chart').style.display = 'none';
}

/* ======================================================================
 * TEXT TOGGLING
 * ======================================================================
 */

/* Toggles the inner HTML of the element given by ID between the two arguments
 */
function togHTML(id, a, b)
{
    var d = document.getElementById(id);
    if (trim(d.innerHTML) == a)
        d.innerHTML = b;
    else
        d.innerHTML = a;
}

/* ======================================================================
 * CHECKBOX TOGGLING
 * ======================================================================
 */

/* Sets all checkboxes to checked=val. If the prefix argument is nonempty, the name of the checkbox must have
 * that as prefix.
 */
function mark_all(val, prefix)
{
    var list = document.getElementsByTagName('input');
    for (var i = 0; i < list.length; i++)
        if (list[i].getAttribute('type') == 'checkbox')
            if (prefix == '' || list[i].name.indexOf(prefix) === 0)
                list[i].checked = val;
}

/* ======================================================================
 * MENU
 * ======================================================================
 */
$(function () {
    var allMenu = $('.menu > ul > li > ul');
    var menuHandler = function(){
            var menu = $(this).parent().next();
            if (menu.is(':visible')) {
                allMenu.hide();
            }
            else {
                allMenu.hide();
                menu.show();
            }
            $(document).one('click', function () {
                menu.hide();
            });
            return false;        
    };
    if (/Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
        $(".actionSelector").removeAttr("style");
        $('.menu > ul > li > div > a').next().button({
            text: false,
            icons: {
                primary: 'ui-icon-triangle-1-s'
            }
        }).click(menuHandler)
        .parent().next().buttonset().hide().menu();
        allMenu.parent().css({ "paddingLeft": "0.1em", "paddingRight": "0.1em" });
    }
    else {        
        $('.menu > ul > li > div > a').hover(menuHandler)
        .parent().next().buttonset().hide().menu();
    }
});
/* ======================================================================
 * AUTOCOMPLETE SEARCH TEXTBOX
 * ======================================================================
 */
var aligulacAutocompleteTemplates = function (ajaxobject) {
    if ((!ajaxobject.tag) && (!ajaxobject.name) && (!ajaxobject.fullname)) {
        return '<span class="autocomplete-header">' + ajaxobject.label + '</span>';
    }
    switch (ajaxobject.type) {
        case 'player':
            ajaxobject.key = ajaxobject.tag + ' ' + ajaxobject.id;
            var team = '';
            if (ajaxobject.teams && ajaxobject.teams.length > 0) {
                team = ajaxobject.teams[0];
                if (team[1] == '')
                    team = team[0];
                else
                    team = team[0];  // + ' (' + team[1] + ')';
                team = '<span class="right">' + team + '</span>';
            }
            return '<a>{aligulac-flag}<img class="btm" src="{aligulac-race}" />{aligulac-name}{aligulac-team}</a>'.replace('{aligulac-flag}',
               ajaxobject.country ? '<img src="' + flagsDir + ajaxobject.country.toLowerCase() + '.png" />' : ' ')
            .replace('{aligulac-race}', racesDir + ajaxobject.race.toUpperCase() + '.png')
            .replace('{aligulac-name}', ajaxobject.tag)
            .replace('{aligulac-team}', team);
        case 'team':
            ajaxobject.key = ajaxobject.name;
            return '<a>{aligulac-name}</a>'
            .replace('{aligulac-name}', ajaxobject.name);
        case 'event':
            ajaxobject.key = ajaxobject.fullname;
            return '<a>{aligulac-name}</a>'
            .replace('{aligulac-name}', ajaxobject.fullname);
    }
    return '<a>' + ajaxobject.value + '</a>';
};
var getResults = function (term, restrict_to) {

    if (!restrict_to)
        restrict_to = ['players', 'teams', 'events'];
    if (typeof(restrict_to) == 'string')
        restrict_to = [restrict_to];
    var deferred = $.Deferred()
    var url = '/search/json/';
    $.ajax({
        type: 'GET',
        url: url,
        dataType: 'json',
        data: { q: term, search_for: restrict_to.join(',') }
    }).success(function (ajaxData) {
        deferred.resolve(ajaxData);
    });

    return deferred;
};

$(document).ready(function () {

    $('#SearchTextBox').autocomplete({
        source: function (request, response) {

            $.when(getResults(request.term)).then(function (result) {

                    var playerresult = [];
                    var teamresult = [];
                    var eventresult = [];
                    if (result.players != undefined && result.players.length > 0) {
                        playerresult = [{ label: 'Players' }].concat(result.players);
                        for (var i = 1; i < playerresult.length; i++)
                            playerresult[i].type = 'player';
                    }
                    if (result.teams != undefined && result.teams.length > 0) {
                        teamresult = [{ label: 'Teams' }].concat(result.teams);
                        for (var i = 1; i < teamresult.length; i++)
                            teamresult[i].type = 'team';
                    }
                    if (result.events != undefined && result.events.length > 0) {
                        eventresult = [{ label: 'Events' }].concat(result.events);
                        for (var i = 1; i < eventresult.length; i++)
                            eventresult[i].type = 'event';
                    }
                    var data = playerresult.concat(teamresult.concat(eventresult));
                    response(data);
                });

        },
        minLength: 2,
        select: function (event, ui) {
            $('#SearchTextBox').val(ui.item.key)
                .closest('form')
                .submit();
            return false;
        },
        open: function () {
            $('.ui-menu')
                .width('auto');
        }
    }).data('ui-autocomplete')._renderItem = function (ul, item) {
        return $('<li></li>')
            .append(aligulacAutocompleteTemplates(item))
            .appendTo(ul);
    };
});

/* ======================================================================
 * AUTOCOMPLETE PREDICTIONS
 * ======================================================================
 */
$(document).ready(function () {
    var $idPalyersTextArea = $("#id_players");
    $idPalyersTextArea.tagsInput({
        autocomplete_opt: {
            minLength: 2,
            select: function (event, ui) {
                $idPalyersTextArea.addTag(ui.item.key);
                $("#id_players_tag").focus();
                return false;
            },
            open: function () {
                $('.ui-menu')
                    .width('auto');
            }
        },
        autocomplete_url: function (request, response) {
            $.when(getResults(request.term, 'players')).then(function (result) {
                if (result.players != undefined) {
                    for (var i = 0; i < result.players.length; i++) {
                        result.players[i].type = 'player';
                    }
                }
                response(result.players);
            });
        },
        defaultText: 'add a player',
        delimiter: '\n',
        formatAutocomplete: aligulacAutocompleteTemplates
    })
    // Hacking the enter key down to submit the form when the
    // current input is empty
    $("#id_players_addTag").keydown(function (event) {
        if (event.which == 13 && $("#id_players_tag").val() == "")
            $(this).closest("form").submit();
    });
});
