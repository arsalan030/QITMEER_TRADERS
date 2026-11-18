from odoo import fields, models


class PartnerBrandPricelist(models.Model):
    _name = 'res.partner.brand.pricelist'
    _description = 'Customer Pricelist per Brand'
    _order = 'partner_id, brand_id'

    partner_id = fields.Many2one(
        'res.partner', string='Customer', required=True, ondelete='cascade', index=True)
    brand_id = fields.Many2one('product.brand', string='Brand', required=True, ondelete='cascade')
    pricelist_id = fields.Many2one(
        'product.pricelist', string='Pricelist', required=True, ondelete='restrict')
    currency_id = fields.Many2one(related='pricelist_id.currency_id')

    _partner_brand_unique = models.Constraint(
        'UNIQUE(partner_id, brand_id)',
        'Only one pricelist per brand per customer.',
    )


class ResPartner(models.Model):
    _inherit = 'res.partner'

    brand_pricelist_ids = fields.One2many(
        'res.partner.brand.pricelist', 'partner_id', string='Brand Pricelists')
