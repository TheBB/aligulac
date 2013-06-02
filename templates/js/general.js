/* ======================================================================
 * GENERAL STUFF
 * ======================================================================
 */

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

function toggle_infobox()
{
    if (document.getElementsByClassName('infobox'))
    {
        var elements = document.getElementsByClassName('infobox');
        for(var i = 0, length = elements.length; i < length; i++)
        {
            elements[i].style.display = 'none';
        }
    }
    var elements = document.getElementsByClassName('edit');
    for(var i = 0, length = elements.length; i < length; i++)
    {
        elements[i].style.display = 'table-row';
    }

}

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
