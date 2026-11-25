from odoo import fields, models

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_channel_id = fields.Many2one('delivery.channel', string='Delivery Channel')
    dispatch_person_id = fields.Many2one('hr.employee', string='Dispatch Person')