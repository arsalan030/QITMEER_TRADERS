from odoo import fields, models


class PartnerBrandPricelist(models.Model):
    _name = 'res.partner.brand.pricelist'
    _description = 'Customer Pricelist per Brand'
    _order = 'partner_id, brand_id, id'

    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, ondelete='cascade', index=True)
    brand_id = fields.Many2one('product.brand', string='Brand', required=True, ondelete='cascade')
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', required=True, ondelete='restrict')
    currency_id = fields.Many2one(related='pricelist_id.currency_id')

    # A customer may now have several pricelists for the same brand
    # (the wizard on the order line lets the salesperson choose).
    _partner_brand_pricelist_unique = models.Constraint(
        'UNIQUE(partner_id, brand_id, pricelist_id)',
        'This pricelist is already assigned to this brand for this customer.',
    )

    def init(self):
        # Drop the old "one pricelist per brand per customer" constraint.
        for name in ('res_partner_brand_pricelist_partner_brand_unique',
                     'res_partner_brand_pricelist__partner_brand_unique'):
            self.env.cr.execute(
                f'ALTER TABLE res_partner_brand_pricelist DROP CONSTRAINT IF EXISTS "{name}"')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    brand_pricelist_ids = fields.One2many(
        'res.partner.brand.pricelist', 'partner_id', string='Brand Pricelists')
