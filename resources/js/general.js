/// <reference path="config.js" />
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
    switch (ajaxobject.objectsType) {
        case 'player':
            ajaxobject.key = ajaxobject.tag;
            return '<a>{aligulac-flag}<img src="{aligulac-race}" />{aligulac-name}</a>'.replace('{aligulac-flag}',
               ajaxobject.country ? '<img src="' + aligulacApiConfig.flagsDirectory + ajaxobject.country.toLowerCase() + '.png" />' : ' ')
            .replace('{aligulac-race}', aligulacApiConfig.racesDirectory + ajaxobject.race.toUpperCase() + '.png')
            .replace('{aligulac-name}', ajaxobject.tag);
        case 'team':
            ajaxobject.key = ajaxobject.name;
            return '<a>{aligulac-name}</a>'
            .replace('{aligulac-name}', ajaxobject.name);
        case 'event':
            ajaxobject.key = ajaxobject.name;
            return '<a>{aligulac-name}</a>'
            .replace('{aligulac-name}', ajaxobject.name);
    }
    return '<a>' + ajaxobject.value + '</a>';
};
var getResults = function (itemToSearch, searchKey, term, label) {
    var deferred = $.Deferred();
    var eventString = (itemToSearch.toLowerCase() == 'event' ? '&type__iexact=event' : '');
    var url = aligulacApiConfig.aligulacApiRoot + itemToSearch +
        '/?' +
        searchKey + '__icontains=' +
        term + eventString
        + '&callback=?';
    $.ajax({
        type: 'GET',
        url: url,
        dataType: 'json',
        data:
        {
            apikey: aligulacApiConfig.apiKey,
            limit: 5
        },
    }).success(function (ajaxData) {
        ajaxData.objects.unshift(label);
        for (var i = 0; i < ajaxData.objects.length; i++) {
            ajaxData.objects[i].objectsType = itemToSearch;
        }
        deferred.resolve({ result: ajaxData.objects });
    });

    return deferred;
};
$(document).ready(function () {
    
    $('#SearchTextBox').autocomplete({
        source: function (request, response) {

            $.when(getResults('player', 'tag', request.term, 'Players'),
                getResults('team', 'name', request.term, 'Teams'),
                getResults('event', 'fullname', request.term, 'Events')).then(function (resplayers, resteams, resevent) {
                    var playerresult = [];
                    var teamresult = [];
                    var eventresult = [];
                    if (resplayers.result.length > 1) {
                        playerresult = resplayers.result;
                    }
                    if (resteams.result.length > 1) {
                        teamresult = resteams.result;
                    }
                    if (resevent.result.length > 1) {
                        eventresult = resevent.result;
                    }
                    var data = playerresult.concat(teamresult.concat(eventresult));
                    response(data);
                });

        },
        minLength: 2,
        select: function (event, ui) {
            $('#SearchTextBox').val(ui.item.key);
            return false;
        }
    }).data('ui-autocomplete')._renderItem = function (ul, item) {
        return $('"<li></li>')
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
                $idPalyersTextArea.addTag(ui.item.key + ' ' + ui.item.id);
                return false;
            }
        },
        autocomplete_url: function (request, response) {
            $.when(getResults('player', 'tag', request.term, 'Players')).then(function (resplayers) {
                response(resplayers.result);
            });
        },
        defaultText: 'add a player',
        delimiter: '\n',
        formatAutocomplete: aligulacAutocompleteTemplates
    });
});