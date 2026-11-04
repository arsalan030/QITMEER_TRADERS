from odoo import models, fields, api
from odoo.tools import html2plaintext


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    product_default_code = fields.Char(
        string='Internal Code',
        related='product_id.default_code',
        readonly=True,
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
        readonly=True,
    )
    location_id = fields.Many2one(
        'stock.location',
        string='Location',
    )
    unit_quantity = fields.Float(
        string='Unit Quantity',
        compute='_compute_unit_quantity',
        store=False,
        readonly=True,
    )
    fixed_amount = fields.Float(
        string='Fixed Amount',
        digits='Product Price',
    )
    discount_mode = fields.Selection(
        [('percent', 'Percent'), ('amount', 'Amount')],
        string='Discount Mode',
        copy=True,
    )

    @api.depends('product_id')
    def _compute_product_ref_id(self):
        for line in self:
            line.product_ref_id = line.product_id

    def _inverse_product_ref_id(self):
        for line in self:
            if line.product_ref_id and line.product_id != line.product_ref_id:
                line.product_id = line.product_ref_id

    @api.onchange('product_ref_id')
    def _onchange_product_ref_id(self):
        for line in self:
            if line.product_ref_id and line.product_id != line.product_ref_id:
                line.product_id = line.product_ref_id
                line._apply_supplierinfo()

    @api.onchange('product_id')
    def _onchange_product_id_set_internal_notes(self):
        # Jab search se product select ho, to Notes set ho jayen
        for line in self:
            if line.product_id:
                note = html2plaintext(line.product_id.description or '').strip()
                if note:
                    line.name = note
                else:
                    line.name = line.product_id.name or ''

    def _get_supplierinfo(self):
        self.ensure_one()
        if not self.product_id or not self.order_id.partner_id:
            return self.env['product.supplierinfo']
        partner_id = self.order_id.partner_id.id
        tmpl_id = self.product_id.product_tmpl_id.id
        supplierinfo = self.env['product.supplierinfo'].search([
            ('extra_partner_ids', 'in', [partner_id]),
            ('extra_product_tmpl_ids', 'in', [tmpl_id]),
        ], limit=1)
        if not supplierinfo:
            supplierinfo = self.env['product.supplierinfo'].search([
                ('partner_id', '=', partner_id),
                ('product_tmpl_id', '=', tmpl_id),
            ], limit=1)
        return supplierinfo

    def _apply_supplierinfo(self):
        for line in self:
            supplierinfo = line._get_supplierinfo()
            if not supplierinfo:
                line.fixed_amount = 0.0
                line.discount_mode = False
                continue
            if supplierinfo.min_qty:
                line.product_uom_qty = supplierinfo.min_qty
            line.price_unit = supplierinfo.price
            line.technical_price_unit = supplierinfo.price
            if supplierinfo.discount_mode == 'amount' and supplierinfo.discount_amount:
                line.fixed_amount = supplierinfo.discount_amount
                line.discount_mode = 'amount'
                line.discount = min(
                    supplierinfo.discount_amount / supplierinfo.price * 100.0,
                    100.0,
                ) if supplierinfo.price else 0.0
            elif supplierinfo.discount_mode == 'percent' or supplierinfo.discount:
                line.discount = supplierinfo.discount
                line.discount_mode = 'percent'
                line.fixed_amount = supplierinfo.price * supplierinfo.discount / 100.0
            elif supplierinfo.discount_amount:
                line.fixed_amount = supplierinfo.discount_amount
                line.discount_mode = 'amount'
                line.discount = min(
                    supplierinfo.discount_amount / supplierinfo.price * 100.0,
                    100.0,
                ) if supplierinfo.price else 0.0
            else:
                line.discount = 0.0
                line.fixed_amount = 0.0
                line.discount_mode = False

    @api.onchange('product_id')
    def _onchange_product_id(self):
        result = super()._onchange_product_id()
        self._apply_supplierinfo()
        return result

    @api.onchange('order_partner_id')
    def _onchange_order_apply_supplierinfo(self):
        self._apply_supplierinfo()

    @api.depends('product_id', 'product_uom_id', 'product_uom_qty', 'order_partner_id')
    def _compute_price_unit(self):
        result = super()._compute_price_unit()
        for line in self:
            supplierinfo = line._get_supplierinfo()
            if supplierinfo:
                line.price_unit = supplierinfo.price
                line.technical_price_unit = supplierinfo.price
        return result

    @api.depends('product_id', 'product_uom_id', 'product_uom_qty', 'order_partner_id')
    def _compute_discount(self):
        result = super()._compute_discount()
        for line in self:
            supplierinfo = line._get_supplierinfo()
            if not supplierinfo:
                continue
            if supplierinfo.discount_mode == 'amount':
                line.fixed_amount = supplierinfo.discount_amount
                line.discount_mode = 'amount' if supplierinfo.discount_amount else False
                line.discount = min(
                    supplierinfo.discount_amount / supplierinfo.price * 100.0,
                    100.0,
                ) if supplierinfo.price else 0.0
            else:
                line.discount = supplierinfo.discount
                line.discount_mode = 'percent' if supplierinfo.discount else False
                line.fixed_amount = supplierinfo.price * supplierinfo.discount / 100.0
        return result

    @api.depends('product_id', 'linked_line_id', 'linked_line_ids')
    def _compute_name(self):
        res = super(SaleOrderLine, self.with_context(internal_ref_search=False))._compute_name()
        for line in self:
            if not line.product_id:
                continue
            note = html2plaintext(line.product_id.description or '').strip()
            if note:
                line.name = note
        return res

    @api.onchange('product_uom_qty')
    def _onchange_product_uom_qty_update_price(self):
        for line in self:
            if line.product_id and line.product_uom_id:
                supplierinfo = line._get_supplierinfo()
                if supplierinfo:
                    line.price_unit = supplierinfo.price
                    line.technical_price_unit = supplierinfo.price
                else:
                    line.price_unit = line.technical_price_unit * max(line.product_uom_qty, 1)

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
                qty = line.product_uom_qty or 0.0
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

    @api.onchange('discount')
    def _onchange_discount_set_fixed(self):
        for line in self:
            if line.discount_mode == 'amount':
                continue
            line.discount_mode = 'percent' if line.discount else False
            line.fixed_amount = (line.price_unit or 0.0) * (line.discount or 0.0) / 100.0

    @api.onchange('fixed_amount')
    def _onchange_fixed_amount_set_discount(self):
        for line in self:
            if line.discount_mode == 'percent':
                continue
            if line.fixed_amount:
                line.discount_mode = 'amount'
                price = line.price_unit or 0.0
                line.discount = min(line.fixed_amount / price * 100.0, 100.0) if price else 0.0
            else:
                line.discount_mode = False
                line.discount = 0.0

    @api.onchange('price_unit')
    def _onchange_price_unit_sync_discount(self):
        for line in self:
            price = line.price_unit or 0.0
            if line.discount_mode == 'amount':
                line.discount = min((line.fixed_amount or 0.0) / price * 100.0, 100.0) if price else 0.0
            else:
                line.fixed_amount = price * (line.discount or 0.0) / 100.0