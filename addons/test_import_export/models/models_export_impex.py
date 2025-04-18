from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


def selection_fn(self):
    return [(str(key), val) for key, val in enumerate([_("Corge"), _("Grault"), _("Wheee"), _("Moog")])]


def compute_fn(records):
    for record in records:
        record.value = 3


def inverse_fn(records):
    pass


MODELS = [
    ('boolean', fields.Boolean()),
    ('integer', fields.Integer(default=4)),
    ('float', fields.Float()),
    ('decimal', fields.Float(digits=(16, 3))),
    ('string.bounded', fields.Char(size=16)),
    ('string.required', fields.Char(size=None, required=True)),
    ('string', fields.Char(size=None)),
    ('date', fields.Date()),
    ('datetime', fields.Datetime()),
    ('text', fields.Text()),
    ('selection', fields.Selection([('1', "Foo"), ('2', "Bar"), ('3', "Qux"), ('4', '')])),
    ('selection.function', fields.Selection(selection_fn)),
    # just relate to an integer
    ('many2one', fields.Many2one('export.integer')),
    ('one2many', fields.One2many('export.one2many.child', 'parent_id')),
    ('many2many', fields.Many2many('export.many2many.other')),
    ('function', fields.Integer(compute=compute_fn, inverse=inverse_fn)),
    # related: specialization of fields.function, should work the same way
    ('reference', fields.Reference([('export.integer', 'integer')], 'export.reference')),
]


def generic_compute_display_name(self):
    for record in self:
        record.display_name = f"{self._name}:{record.value}"


def generic_search_display_name(self, operator, value):
    if operator != 'in':
        return NotImplemented
    ids = [
        int(id_str)
        for v in value
        if isinstance(v, str)
        and (parts := v.split(':'))
        and len(parts) == 2
        and parts[0] == self._name
        and (id_str := parts[1]).isdigit()
    ]
    return [('value', 'in', ids)]


for name, field in MODELS:

    class NewModel(models.Model):
        _name = f'export.{name}'
        _description = f'Export: {name}'
        _rec_name = 'value'
        const = fields.Integer(default=4)
        value = field

        _compute_display_name = generic_compute_display_name
        _search_display_name = generic_search_display_name


class ExportOne2manyChild(models.Model):
    _name = 'export.one2many.child'
    _description = 'Export One to Many Child'
    # FIXME: orm.py:1161, fix to display_name on m2o field
    _rec_name = 'value'

    parent_id = fields.Many2one('export.one2many')
    str = fields.Char()
    m2o = fields.Many2one('export.integer')
    value = fields.Integer()

    _compute_display_name = generic_compute_display_name
    _search_display_name = generic_search_display_name


class ExportOne2manyMultiple(models.Model):
    _name = 'export.one2many.multiple'
    _description = 'Export One To Many Multiple'
    _rec_name = 'parent_id'

    parent_id = fields.Many2one('export.one2many.recursive')
    const = fields.Integer(default=36)
    child1 = fields.One2many('export.one2many.child.1', 'parent_id')
    child2 = fields.One2many('export.one2many.child.2', 'parent_id')


class ExportOne2manyMultipleChild(models.Model):
    # FIXME: orm.py:1161, fix to display_name on m2o field
    _rec_name = 'value'
    _name = 'export.one2many.multiple.child'
    _description = 'Export One To Many Multiple Child'

    parent_id = fields.Many2one('export.one2many.multiple')
    str = fields.Char()
    value = fields.Integer()

    def _compute_display_name(self):
        for record in self:
            record.display_name = f"{self._name}:{record.value}"


class ExportOne2manyChild1(models.Model):
    _name = 'export.one2many.child.1'
    _inherit = ['export.one2many.multiple.child']
    _description = 'Export One to Many Child 1'


class ExportOne2manyChild2(models.Model):
    _name = 'export.one2many.child.2'
    _inherit = ['export.one2many.multiple.child']
    _description = 'Export One To Many Child 2'


class ExportMany2manyOther(models.Model):
    _name = 'export.many2many.other'
    _description = 'Export Many to Many Other'
    # FIXME: orm.py:1161, fix to display_name on m2o field
    _rec_name = 'value'

    str = fields.Char()
    value = fields.Integer()

    _compute_display_name = generic_compute_display_name
    _search_display_name = generic_search_display_name


class ExportSelectionWithdefault(models.Model):
    _name = 'export.selection.withdefault'
    _description = 'Export Selection With Default'

    const = fields.Integer(default=4)
    value = fields.Selection([('1', "Foo"), ('2', "Bar")], default='2')


class ExportOne2manyRecursive(models.Model):
    _name = 'export.one2many.recursive'
    _description = 'Export One To Many Recursive'
    _rec_name = 'value'

    value = fields.Integer()
    child = fields.One2many('export.one2many.multiple', 'parent_id')


class ExportUnique(models.Model):
    _name = 'export.unique'
    _description = 'Export Unique'

    value = fields.Integer()
    value2 = fields.Integer()
    value3 = fields.Integer()

    _value_unique = models.Constraint('unique (value)')
    _pair_unique = models.Constraint('unique (value2, value3)')


class ExportInheritsParent(models.Model):
    _name = 'export.inherits.parent'
    _description = 'export.inherits.parent'

    value_parent = fields.Integer()


class ExportInheritsChild(models.Model):
    _name = 'export.inherits.child'
    _description = 'export.inherits.child'
    _inherits = {'export.inherits.parent': 'parent_id'}

    parent_id = fields.Many2one('export.inherits.parent', required=True, ondelete='cascade')
    value = fields.Integer()


class ExportM2oStr(models.Model):
    _name = 'export.m2o.str'
    _description = 'export.m2o.str'

    child_id = fields.Many2one('export.m2o.str.child')


class ExportM2oStrChild(models.Model):
    _name = 'export.m2o.str.child'
    _description = 'export.m2o.str.child'

    name = fields.Char()


class ExportWithRequiredField(models.Model):
    _name = 'export.with.required.field'
    _description = 'export.with.required.field'

    name = fields.Char()
    value = fields.Integer(required=True)


class ExportMany2oneRequiredSubfield(models.Model):
    _name = 'export.many2one.required.subfield'
    _description = 'export.many2one.required.subfield'

    name = fields.Many2one('export.with.required.field')


class WithNonDemoConstraint(models.Model):
    _name = 'export.with.non.demo.constraint'
    _description = 'export.with.non.demo.constraint'

    name = fields.Char()

    @api.constrains('name')
    def _check_name_starts_with_uppercase_except_demo_data(self):
        if self.env.context.get('install_mode'):
            return  # skipped on demo data
        if any(rec.name and rec.name[0].islower() for rec in self):
            raise ValidationError('Name must start with an uppercase letter')
