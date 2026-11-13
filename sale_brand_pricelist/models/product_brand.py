from odoo import fields, models


class ProductBrand(models.Model):
    _name = 'product.brand'
    _description = 'Product Brand'
    _order = 'name'

    name = fields.Char(required=True, translate=True)
    active = fields.Boolean(default=True)
    product_tmpl_ids = fields.One2many('product.template', 'brand_id', string='Products')
    product_count = fields.Integer(compute='_compute_product_count')

    _name_unique = models.Constraint(
        'UNIQUE(name)',
        'A brand with this name already exists.',
    )

    def _compute_product_count(self):
        data = self.env['product.template']._read_group(
            [('brand_id', 'in', self.ids)], ['brand_id'], ['__count'])
        counts = {brand.id: count for brand, count in data}
        for brand in self:
            brand.product_count = counts.get(brand.id, 0)

    def action_view_products(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name,
            'res_model': 'product.template',
            'view_mode': 'list,form',
            'domain': [('brand_id', '=', self.id)],
            'context': {'default_brand_id': self.id},
        }
