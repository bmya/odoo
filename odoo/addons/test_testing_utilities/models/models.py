from itertools import zip_longest

from odoo import api, fields, models, Command


class Test_Testing_UtilitiesA(models.Model):
    _name = 'test_testing_utilities.a'
    _description = 'Testing Utilities A'

    f1 = fields.Char(required=True)
    f2 = fields.Integer(default=42)
    f3 = fields.Integer()
    f4 = fields.Integer(compute='_compute_f4')
    f5 = fields.Integer()
    f6 = fields.Integer()

    @api.onchange('f2')
    def _on_change_f2(self):
        self.f3 = int(self.f2 / 2)
        self.f5 = self.f2
        self.f6 = self.f2

    @api.depends('f1', 'f2')
    def _compute_f4(self):
        for r in self:
            r.f4 = r.f2 / (int(r.f1) or 1)


class Test_Testing_UtilitiesReadonly(models.Model):
    _name = 'test_testing_utilities.readonly'
    _description = 'Testing Utilities Readonly'

    f1 = fields.Integer(default=1, readonly=True)
    f2 = fields.Integer(compute='_compute_f2')

    @api.depends('f1')
    def _compute_f2(self):
        for r in self:
            r.f2 = 2 * r.f1


class Test_Testing_UtilitiesC(models.Model):
    _name = 'test_testing_utilities.c'
    _description = 'Testing Utilities C'

    name = fields.Char("name", required=True)
    f2 = fields.Many2one('test_testing_utilities.m2o')

    @api.onchange('f2')
    def _on_change_f2(self):
        self.name = self.f2.name


class Test_Testing_UtilitiesM2o(models.Model):
    _name = 'test_testing_utilities.m2o'
    _description = 'Testing Utilities Many To One'

    name = fields.Char(required=True)


class Test_Testing_UtilitiesD(models.Model):
    _name = 'test_testing_utilities.d'
    _description = 'Testing Utilities D'

    # used to check that defaults & onchange to m2o work
    f = fields.Many2one(
        'test_testing_utilities.m2o',
        required=True,
        default=lambda self: self.env['test_testing_utilities.m2o'].search(
            [], limit=1
        )
    )
    f2 = fields.Char()

    @api.onchange('f2')
    def _on_change_f2(self):
        self.f = self.env['test_testing_utilities.m2o'].search([
            ('name', 'ilike', self.f2),
        ], limit=1) if self.f2 else False


class Test_Testing_UtilitiesE(models.Model):
    _name = 'test_testing_utilities.e'
    _description = 'Testing Utilities E'

    m2m = fields.Many2many('test_testing_utilities.sub2')
    count = fields.Integer(compute='_m2m_count', inverse='_set_count')

    @api.depends('m2m')
    def _m2m_count(self):
        for r in self:
            r.count = len(r.m2m)

    def _set_count(self):
        for r in self:
            r.write({
                'm2m': [
                    Command.create({'name': str(n)})
                    for n, v in zip_longest(range(r.count), r.m2m or [])
                    if v is None
                ]
            })


class Test_Testing_UtilitiesSub2(models.Model):
    _name = 'test_testing_utilities.sub2'
    _description = 'Testing Utilities Subtraction 2'

    name = fields.Char()
    m2o_ids = fields.Many2many('test_testing_utilities.m2o')


class Test_Testing_UtilitiesF(models.Model):
    _name = 'test_testing_utilities.f'
    _description = 'Testing Utilities F'

    def _get_some(self):
        r = self.env['test_testing_utilities.sub2'].search([], limit=2)
        return r

    m2m = fields.Many2many(
        'test_testing_utilities.sub2',
        default=_get_some,
    )
    m2o = fields.Many2one('test_testing_utilities.sub2')

    @api.onchange('m2o')
    def _on_change_m2o(self):
        self.m2m = self.m2m | self.m2o


class Test_Testing_UtilitiesG(models.Model):
    _name = 'test_testing_utilities.g'
    _description = 'Testing Utilities G'

    m2m = fields.Many2many('test_testing_utilities.sub3', readonly=True)


class Test_Testing_UtilitiesSub3(models.Model):
    _name = 'test_testing_utilities.sub3'
    _description = 'Testing Utilities Subtraction 3'

    name = fields.Char()


class Test_Testing_UtilitiesParent(models.Model):
    _name = 'test_testing_utilities.parent'
    _description = 'Testing Utilities Parent'

    value = fields.Integer(default=1)
    v = fields.Integer()
    subs = fields.One2many('test_testing_utilities.sub', 'parent_id')

    @api.onchange('value', 'subs')
    def _onchange_values(self):
        self.v = self.value + sum(s.value for s in self.subs)


class Test_Testing_UtilitiesSub(models.Model):
    _name = 'test_testing_utilities.sub'
    _description = 'Testing Utilities Subtraction'

    name = fields.Char(compute='_compute_name')
    value = fields.Integer(default=2)
    v = fields.Integer()
    parent_id = fields.Many2one('test_testing_utilities.parent')
    has_parent = fields.Boolean()

    @api.onchange('value')
    def _onchange_value(self):
        self.v = self.value

    @api.depends('v')
    def _compute_name(self):
        for r in self:
            r.name = str(r.v)

    @api.onchange('has_parent')
    def _onchange_has_parent(self):
        if self.has_parent:
            self.value = self.parent_id.value


class Test_Testing_UtilitiesRef(models.Model):
    _name = 'test_testing_utilities.ref'
    _description = 'Testing Utilities ref'

    value = fields.Integer(default=1)
    subs = fields.One2many('test_testing_utilities.ref.sub', 'parent_id')
    x = fields.Integer()


class Test_Testing_UtilitiesRefSub(models.Model):
    _name = 'test_testing_utilities.ref.sub'
    _description = 'Testing Utilities Subtraction'

    a = fields.Integer()
    b = fields.Integer()
    c = fields.Integer()
    z = fields.Integer()
    parent_id = fields.Many2one('test_testing_utilities.ref')


class Test_Testing_UtilitiesDefault(models.Model):
    _name = 'test_testing_utilities.default'
    _description = 'Testing Utilities Default'

    value = fields.Integer(default=1)
    v = fields.Integer()
    subs = fields.One2many('test_testing_utilities.sub3', 'parent_id', default=lambda self: self._default_subs())

    def _default_subs(self):
        return [
            Command.create({'v': 5})
        ]

    @api.onchange('value')
    def _onchange_value(self):
        if self.value == 42:
            self.subs = False


# pylint: disable=E0102
class Test_Testing_UtilitiesSub3(models.Model):  # noqa: F811
    _name = 'test_testing_utilities.sub3'
    _description = 'Testing Utilities Subtraction 3'

    name = fields.Char(compute='_compute_name')
    value = fields.Integer(default=2)
    v = fields.Integer(default=6)
    parent_id = fields.Many2one('test_testing_utilities.default')

    @api.onchange('value')
    def _onchange_value(self):
        self.v = self.value

    @api.depends('v')
    def _compute_name(self):
        for r in self:
            r.name = str(r.v)


class Test_Testing_UtilitiesRecursive(models.Model):
    _name = 'test_testing_utilities.recursive'
    _description = 'test_testing_utilities.recursive'

    one_to_many_id = fields.Many2one('test_testing_utilities.recursive', readonly=True)
    many_to_one_ids = fields.One2many('test_testing_utilities.recursive', 'one_to_many_id', readonly=True)


class Test_Testing_UtilitiesOnchange_Parent(models.Model):
    _name = 'test_testing_utilities.onchange_parent'
    _description = 'Testing Utilities Onchange Parent'

    line_ids = fields.One2many('test_testing_utilities.onchange_line', 'parent')

    @api.onchange('line_ids')
    def _onchange_line_ids(self):
        for line in self.line_ids.filtered(lambda l: l.flag):
            self.env['test_testing_utilities.onchange_line'].new({'parent': line.id})


class Test_Testing_UtilitiesOnchange_Line(models.Model):
    _name = 'test_testing_utilities.onchange_line'
    _description = "Testing Utilities Onchange Line"

    parent = fields.Many2one('test_testing_utilities.onchange_parent')
    dummy = fields.Float()
    flag = fields.Boolean(store=False)

    @api.onchange('dummy')
    def _onchange_flag(self):
        self.flag = True


class Test_Testing_UtilitiesOnchange_Count(models.Model):
    _name = 'test_testing_utilities.onchange_count'
    _description = "Test_Testing_UtilitiesOnchange_Count"

    count = fields.Integer()
    line_ids = fields.One2many('test_testing_utilities.onchange_count_sub', 'parent')

    @api.onchange('count')
    def _onchange_count(self):
        Sub = self.env['test_testing_utilities.onchange_count_sub']
        recs = Sub
        for i in range(self.count):
            recs |= Sub.new({'name': str(i)})
        self.line_ids = recs


class Test_Testing_UtilitiesOnchange_Count_Sub(models.Model):
    _name = 'test_testing_utilities.onchange_count_sub'
    _description = "Test_Testing_UtilitiesOnchange_Count_Sub"

    parent = fields.Many2one('test_testing_utilities.onchange_count')
    name = fields.Char()


class O2m_Readonly_Subfield_Parent(models.Model):
    _name = 'o2m_readonly_subfield_parent'
    _description = "O2m_Readonly_Subfield_Parent"

    line_ids = fields.One2many('o2m_readonly_subfield_child', 'parent_id')


class O2m_Readonly_Subfield_Child(models.Model):
    _name = 'o2m_readonly_subfield_child'
    _description = "o2m_readonly_subfield_child"

    name = fields.Char()
    parent_id = fields.Many2one('o2m_readonly_subfield_parent')
    f = fields.Integer(compute='_compute_f', inverse='_inverse_f', readonly=True)

    @api.depends('name')
    def _compute_f(self):
        for r in self:
            r.f = len(r.name) if r.name else 0

    def _inverse_f(self):
        raise AssertionError("Inverse of f should not be called")


class Test_Testing_UtilitiesReq_Bool(models.Model):
    _name = 'test_testing_utilities.req_bool'
    _description = 'test_testing_utilities.req_bool'

    f_bool = fields.Boolean(required=True)


class O2m_Changes_Parent(models.Model):
    _name = 'o2m_changes_parent'
    _description = 'o2m_changes_parent'

    name = fields.Char()
    line_ids = fields.One2many('o2m_changes_children', 'parent_id')

    @api.onchange('name')
    def _onchange_name(self):
        for line in self.line_ids:
            line.line_ids = [Command.delete(l.id) for l in line.line_ids] + [
                Command.create({'v': 0, 'vv': 0})
            ]


class O2m_Changes_Children(models.Model):
    _name = 'o2m_changes_children'
    _description = 'o2m_changes_children'

    name = fields.Char()
    v = fields.Integer()
    line_ids = fields.One2many('o2m_changes_children.lines', 'parent_id')
    parent_id = fields.Many2one('o2m_changes_parent')

    @api.onchange('v')
    def _onchange_v(self):
        for record in self:
            for line in record.line_ids:
                line.v = record.v


class O2m_Changes_ChildrenLines(models.Model):
    _name = 'o2m_changes_children.lines'
    _description = 'o2m_changes_children.lines'

    parent_id = fields.Many2one('o2m_changes_children')
    v = fields.Integer()
    vv = fields.Integer()


class ResConfigTest(models.Model):
    _name = 'res.config.test'
    _inherit = ['res.config.settings']

    _description = 'Config test'

    param1 = fields.Integer(
        string='Test parameter 1',
        config_parameter='resConfigTest.parameter1',
        default=1000)

    param2 = fields.Many2one(
        'res.config',
        config_parameter="resConfigTest.parameter2")


class Test_Testing_UtilitiesWide(models.Model):
    _name = 'test_testing_utilities.wide'
    _description = 'test_testing_utilities.wide'
    _log_access = False

    account_id = fields.Float()
    amount_currency = fields.Float()
    credit = fields.Float()
    currency_id = fields.Float()
    date_maturity = fields.Float()
    debit = fields.Float()
    discount = fields.Float()
    name = fields.Float()
    partner_id = fields.Float()
    price_subtotal = fields.Float()
    price_total = fields.Float()
    price_unit = fields.Float()
    product_id = fields.Float()
    product_uom_id = fields.Float()
    quantity = fields.Float()
    tax_base_amount = fields.Float()
    tax_ids = fields.Float()
    tax_line_id = fields.Float()
    tax_tag_invert = fields.Float()
