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

/* Makes all elements given in the all array invisible except for the one given by id
 */
function switch_to(id, all)
{
    for (i = 0; i < all.length; i++)
    {
        if (all[i] == id)
            document.getElementById(all[i]).style.display = 'block';
        else
            document.getElementById(all[i]).style.display = 'none';
    }
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
