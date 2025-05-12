from odoo import models, fields, api

class PlannificateurReappro(models.Model):
    _name = 'plannificateur.reappro'
    _description = 'Planificateur de réapprovisionnement'

    name = fields.Char(string='Nom', required=True)
    date_planification = fields.Date(string='Date de planification', default=fields.Date.today)
    product_id = fields.Many2one('product.product', string='Produit', required=True)
    quantite = fields.Float(string='Quantité à commander', required=True)
    state = fields.Selection([
        ('draft', 'Brouillon'),
        ('confirmed', 'Confirmé'),
        ('done', 'Terminé')
    ], string='État', default='draft')

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('plannificateur.reappro') or 'Nouveau'
        return super(PlannificateurReappro, self).create(vals) 