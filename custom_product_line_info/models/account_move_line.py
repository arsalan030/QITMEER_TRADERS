from odoo import models, fields, api


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    product_default_code = fields.Char(
        string='Internal Code',
        related='product_id.default_code',
        readonly=True
    )
    product_ref_id = fields.Many2one(
        'product.product',
        string='Internal Reference',
        compute='_compute_product_ref_id',
        inverse='_inverse_product_ref_id',
        readonly=False,
        store=False,
    )
    product_description = fields.Text(
        string='Product Description',
        related='name',
        readonly=True
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location'
    )
    unit_quantity = fields.Float(
        string='Unit Quantity',
        compute='_compute_unit_quantity',
        store=False,
        readonly=True
    )

    @api.depends('product_id')
    def _compute_product_ref_id(self):
        for line in self:
            line.product_ref_id = line.product_id

    def _inverse_product_ref_id(self):
        for line in self:
            if line.product_id != line.product_ref_id:
                line.product_id = line.product_ref_id

    @api.onchange('product_ref_id')
    def _onchange_product_ref_id(self):
        for line in self:
            if line.product_id != line.product_ref_id:
                line.product_id = line.product_ref_id
                line._inverse_product_id()

    @api.depends('product_id', 'move_id.ref', 'move_id.payment_reference')
    def _compute_name(self):
        return super(AccountMoveLine, self.with_context(internal_ref_search=False))._compute_name()

    @api.depends('product_id', 'product_id.uom_id', 'product_id.uom_id.parent_path')
    def _compute_allowed_uom_ids(self):
        Uom = self.env['uom.uom']
        multi_uom_enabled = self.env['res.groups']._is_feature_enabled('uom.group_uom')
        for line in self:
            if line.product_id and multi_uom_enabled:
                root_id = line.product_id.uom_id.parent_path.split('/', 1)[0]
                line.allowed_uom_ids = Uom.search([('parent_path', '=like', f'{root_id}/%')])
            else:
                line.allowed_uom_ids = line.product_id._get_available_uoms()

    def _compute_unit_quantity(self):
        uom_field = (
            'product_uom_id' if 'product_uom_id' in self._fields
            else 'product_uom'
        )
        for line in self:
            line.unit_quantity = 0.0
            product = line.product_id
            if not product:
                continue
            try:
                qty = line.quantity or 0.0
                uom = line[uom_field] if uom_field in line._fields else None
                factor = uom.factor or 0.0 if uom else 0.0
                if factor:
                    line.unit_quantity = qty * factor
                else:
                    if product.packaging_ids:
                        line.unit_quantity = product.packaging_ids[0].qty
                    elif product.product_tmpl_id.packaging_ids:
                        line.unit_quantity = product.product_tmpl_id.packaging_ids[0].qty
            except Exception:
                line.unit_quantity = 0.0