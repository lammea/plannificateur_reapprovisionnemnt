from odoo import models, fields, api, tools
from dateutil.relativedelta import relativedelta
from datetime import datetime

class ProductWithBom(models.Model):
    _name = 'product.with.bom'
    _description = 'Produits avec nomenclature'
    _auto = False
    _order = 'month_date, default_code'
    _rec_name = 'month_name'

    product_id = fields.Many2one('product.product', string='Produit', readonly=True)
    product_name = fields.Char(string='Nom du produit', readonly=True)
    default_code = fields.Char(string='Référence', readonly=True)
    month_date = fields.Date(string='Date du mois', readonly=True)
    month_name = fields.Char(string='Mois', readonly=True, group_operator="min")
    previous_year_sales = fields.Float(string='Ventes N-1', readonly=True)
    forecast_qty = fields.Float(string='Prévisions', readonly=False)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                WITH RECURSIVE months AS (
                    -- On commence par le premier jour du mois actuel
                    SELECT date_trunc('month', CURRENT_DATE) AS month_date
                    UNION ALL
                    -- On ajoute les mois sur 5 ans pour avoir une vision à long terme
                    SELECT month_date + interval '1 month'
                    FROM months
                    WHERE month_date < date_trunc('month', CURRENT_DATE) + interval '5 years'
                ),
                previous_year_sales AS (
                    SELECT 
                        sol.product_id,
                        date_trunc('month', so.date_order) as sale_month,
                        sum(sol.product_uom_qty) as qty_sold
                    FROM 
                        sale_order_line sol
                        JOIN sale_order so ON so.id = sol.order_id
                    WHERE 
                        so.state in ('sale', 'done')
                        AND so.date_order >= (CURRENT_DATE - interval '1 year')::date
                        AND so.date_order < CURRENT_DATE
                    GROUP BY 
                        sol.product_id,
                        date_trunc('month', so.date_order)
                )
                SELECT DISTINCT ON (m.month_date, pp.id)
                    ROW_NUMBER() OVER (ORDER BY m.month_date, pp.default_code) as id,
                    pp.id as product_id,
                    pt.name as product_name,
                    pp.default_code,
                    m.month_date,
                    to_char(m.month_date, 'TMMonth YYYY') as month_name,
                    COALESCE(pys.qty_sold, 0) as previous_year_sales,
                    0 as forecast_qty
                FROM 
                    product_product pp
                JOIN 
                    product_template pt ON pp.product_tmpl_id = pt.id
                JOIN 
                    mrp_bom mb ON mb.product_tmpl_id = pt.id
                CROSS JOIN
                    months m
                LEFT JOIN
                    previous_year_sales pys ON pys.product_id = pp.id 
                    AND EXTRACT(MONTH FROM pys.sale_month) = EXTRACT(MONTH FROM m.month_date)
                WHERE 
                    pt.sale_ok = true
                    AND m.month_date >= date_trunc('month', CURRENT_DATE)
                ORDER BY
                    m.month_date, pp.id, pp.default_code
            )
        """ % self._table)

    def write(self, vals):
        """
        Surcharge de la méthode write pour gérer la sauvegarde des prévisions
        """
        if 'forecast_qty' in vals:
            self.env['product.forecast'].create({
                'product_id': self.product_id.id,
                'month_date': self.month_date,
                'forecast_qty': vals['forecast_qty']
            })
        return True

class PlannificateurReappro(models.Model):
    _name = 'plannificateur.reappro'
    _description = 'Planificateur de réapprovisionnement'

    @api.depends('periode', 'mois', 'trimestre', 'semestre', 'annee')
    def _get_date_range(self):
        for record in self:
            start_date = False
            end_date = False
            current_date = fields.Date.today()
            current_year = current_date.year

            if record.periode == 'mensuel' and record.mois:
                month = int(record.mois)
                year = current_year
                if record.annee:
                    year = int(record.annee)
                elif month < current_date.month:
                    year = current_year + 1
                start_date = fields.Date.to_date(f'{year}-{month:02d}-01')
                end_date = start_date + relativedelta(months=1, days=-1)

            elif record.periode == 'trimestriel' and record.trimestre:
                trimestre = int(record.trimestre)
                start_month = ((trimestre - 1) * 3) + 1
                end_month = start_month + 2
                year = current_year
                if record.annee:
                    year = int(record.annee)
                elif start_month < current_date.month:
                    year = current_year + 1
                start_date = fields.Date.to_date(f'{year}-{start_month:02d}-01')
                if end_month == 12:
                    end_date = fields.Date.to_date(f'{year}-12-31')
                else:
                    end_date = fields.Date.to_date(f'{year}-{end_month:02d}-01') + relativedelta(months=1, days=-1)

            elif record.periode == 'semestriel' and record.semestre:
                semestre = int(record.semestre)
                start_month = ((semestre - 1) * 6) + 1
                year = current_year
                if record.annee:
                    year = int(record.annee)
                elif start_month < current_date.month:
                    year = current_year + 1
                start_date = fields.Date.to_date(f'{year}-{start_month:02d}-01')
                end_date = start_date + relativedelta(months=6, days=-1)

            elif record.periode == 'annuel' and record.annee:
                year = int(record.annee)
                start_date = fields.Date.to_date(f'{year}-01-01')
                end_date = fields.Date.to_date(f'{year}-12-31')
            
            record.date_debut = start_date
            record.date_fin = end_date

    name = fields.Char(string='Nom', required=True)
    periode = fields.Selection([
        ('mensuel', 'Mensuel'),
        ('trimestriel', 'Trimestriel'),
        ('semestriel', 'Semestriel'),
        ('annuel', 'Annuel')
    ], string='Période de réapprovisionnement', required=True)

    date_debut = fields.Date(string='Date de début', compute='_get_date_range', store=True)
    date_fin = fields.Date(string='Date de fin', compute='_get_date_range', store=True)

    # Champs pour la sélection mensuelle
    mois = fields.Selection([
        ('1', 'Janvier'),
        ('2', 'Février'),
        ('3', 'Mars'),
        ('4', 'Avril'),
        ('5', 'Mai'),
        ('6', 'Juin'),
        ('7', 'Juillet'),
        ('8', 'Août'),
        ('9', 'Septembre'),
        ('10', 'Octobre'),
        ('11', 'Novembre'),
        ('12', 'Décembre')
    ], string='Mois')

    # Champs pour la sélection trimestrielle
    trimestre = fields.Selection([
        ('1', '1er Trimestre (Jan-Mar)'),
        ('2', '2ème Trimestre (Avr-Jun)'),
        ('3', '3ème Trimestre (Jul-Sep)'),
        ('4', '4ème Trimestre (Oct-Déc)')
    ], string='Trimestre')

    # Champs pour la sélection semestrielle
    semestre = fields.Selection([
        ('1', '1er Semestre (Jan-Jun)'),
        ('2', '2ème Semestre (Jul-Déc)')
    ], string='Semestre')

    # Champs pour la sélection annuelle
    annee = fields.Selection(
        selection='_get_years',
        string='Année'
    )

    # Champs pour les produits
    product_ids = fields.Many2many(
        'product.with.bom',
        string='Saisie des prévisions'
    )

    show_products = fields.Boolean(compute='_compute_show_products')
    is_future_year = fields.Boolean(compute='_compute_is_future_year', string='Est une année future')
    year_message = fields.Char(compute='_compute_is_future_year', string='Message année')

    @api.depends('periode', 'mois', 'trimestre', 'semestre', 'annee')
    def _compute_show_products(self):
        for record in self:
            if record.periode == 'mensuel' and record.mois:
                record.show_products = True
            elif record.periode == 'trimestriel' and record.trimestre:
                record.show_products = True
            elif record.periode == 'semestriel' and record.semestre:
                record.show_products = True
            elif record.periode == 'annuel' and record.annee:
                record.show_products = True
            else:
                record.show_products = False

    @api.model
    def _get_years(self):
        current_year = fields.Date.today().year
        years = [(str(i), str(i)) for i in range(current_year, current_year + 5)]
        return years

    @api.onchange('periode', 'mois', 'trimestre', 'semestre', 'annee')
    def _onchange_periode(self):
        # Réinitialiser les champs de période non concernés
        if self.periode == 'mensuel':
            self.trimestre = False
            self.semestre = False
            self.annee = False
        elif self.periode == 'trimestriel':
            self.mois = False
            self.semestre = False
            self.annee = False
        elif self.periode == 'semestriel':
            self.mois = False
            self.trimestre = False
            self.annee = False
        elif self.periode == 'annuel':
            self.mois = False
            self.trimestre = False
            self.semestre = False
        
        # Charger automatiquement les produits seulement si la période est complètement sélectionnée
        if self.show_products:
            domain = []
            if self.date_debut and self.date_fin:
                domain = [('month_date', '>=', self.date_debut), ('month_date', '<=', self.date_fin)]
            products = self.env['product.with.bom'].search(domain)
            self.product_ids = [(6, 0, products.ids)]
        else:
            self.product_ids = [(5, 0, 0)]

    @api.depends('periode', 'annee', 'trimestre', 'semestre', 'mois')
    def _compute_is_future_year(self):
        current_year = fields.Date.today().year
        for record in self:
            selected_year = current_year
            if record.annee:
                selected_year = int(record.annee)
            elif record.periode == 'mensuel' and record.mois:
                month = int(record.mois)
                selected_year = current_year if month >= fields.Date.today().month else current_year + 1
            elif record.periode == 'trimestriel' and record.trimestre:
                trimestre = int(record.trimestre)
                start_month = ((trimestre - 1) * 3) + 1
                selected_year = current_year if start_month >= fields.Date.today().month else current_year + 1
            elif record.periode == 'semestriel' and record.semestre:
                semestre = int(record.semestre)
                start_month = ((semestre - 1) * 6) + 1
                selected_year = current_year if start_month >= fields.Date.today().month else current_year + 1
            
            record.is_future_year = selected_year > current_year
            record.year_message = f"Vous consultez l'année {selected_year}"

    @api.model
    def create(self, vals):
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('plannificateur.reappro') or 'Nouveau'
        return super(PlannificateurReappro, self).create(vals)

class ProductForecast(models.Model):
    _name = 'product.forecast'
    _description = 'Prévisions par produit'
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string='Produit', required=True)
    month_date = fields.Date(string='Mois', required=True)
    forecast_qty = fields.Float(string='Quantité prévue', required=True)

    _sql_constraints = [
        ('unique_product_month', 
         'UNIQUE(product_id, month_date)',
         'Une prévision existe déjà pour ce produit ce mois-ci!')
    ] 