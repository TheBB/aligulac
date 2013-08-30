
from django import template
from django.template.base import token_kwargs
from django.template.loader import get_template
from django.template.loader_tags import BlockNode, ExtendsNode, BlockContext

register = template.Library()

def resolve_blocks(template, context, blocks=None):
    '''Get all the blocks from this template, accounting for 'extends' tags'''
    if blocks is None:
        blocks = BlockContext()

    # If it's just the name, resolve into template
    if isinstance(template, str):
        template = get_template(template)

    # Add this templates blocks as the first
    local_blocks = dict(
        (block.name, block)
        for block in template.nodelist.get_nodes_by_type(BlockNode)
    )
    blocks.add_blocks(local_blocks)

    # Do we extend a parent template?
    extends = template.nodelist.get_nodes_by_type(ExtendsNode)
    if extends:
        # Can only have one extends in a template
        extends_node = extends[0]

        # Get the parent, and recurse
        parent_template = extends_node.get_parent(context)
        resolve_blocks(parent_template, context, blocks)

    return blocks

class TempContext(object):
    '''A context manager to make it easy to push context temporarily'''
    def __init__(self, context, update):
        self.context = context
        self.update = update

    def __enter__(self):
        self.context.update(self.update)
        return self.context

    def __exit__(self, exc_type, exc_value, traceback):
        self.context.pop()

@register.tag
def form(parser, token):
    '''Prepare to render a Form, using the specified template.

    {% form "template.form" %}
        {% field form.somefield "blockname" ..... %}
        ...
    {% endform %}
    '''
    bits = token.split_contents()
    tag_name = bits.pop(0) # Remove the tag name
    try:
        tmpl_name = parser.compile_filter(bits.pop(0))
    except IndexError:
        raise template.TemplateSyntaxError("%r tag takes at least 1 argument: the widget template" % tag_name)

    kwargs = token_kwargs(bits, parser)

    nodelist = parser.parse(('endform',))
    parser.delete_first_token()

    return FormNode(tmpl_name, nodelist, kwargs)


class FormNode(template.Node):
    def __init__(self, tmpl_name, nodelist, kwargs):
        self.tmpl_name = tmpl_name
        self.nodelist = nodelist
        self.kwargs = kwargs

    def render(self, context):
        # Resolve our arguments
        tmpl_name = self.tmpl_name.resolve(context)
        kwargs = dict(
            (key, val.resolve(context))
            for key, val in self.kwargs.items()
        )

        # Grab the template snippets
        kwargs['formulation'] = resolve_blocks(tmpl_name, context)

        # Render our children
        with TempContext(context, kwargs) as context:
            return self.nodelist.render(context)


@register.simple_tag(takes_context=True)
def field(context, widget, *fields, **kwargs):
    kwargs['field'] = fields[0]
    kwargs['fields'] = fields
    kwargs['block'] = block = context['formulation'].get_block(widget)
    with TempContext(context, kwargs) as context:
        return block.render(context)


@register.simple_tag(takes_context=True)
def use(context, widget, **kwargs):
    kwargs['block'] = block = context['formulation'].get_block(widget)
    with TempContext(context, kwargs) as context:
        return block.render(context)

