from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime
from dateutil.relativedelta import relativedelta



class Campaign(models.Model):
    _name = 'oui.campaign'
    _description = 'Campagne'
    _order = 'id desc'
    _inherit = ['mail.thread']  # pour tracking state

    name = fields.Char(string="Référence", readonly=True, copy=False)
    client_id = fields.Many2one(
        'res.partner',
        string="Client",
        required=True,
        domain="[('is_company','=',True)]"
    )
    conseiller_ids = fields.Many2many('res.users', string="Conseillers")

    attendee_ids = fields.One2many(
        'calendar.event',
        'campaign_id',
        string="Rendez-vous"
    )
    campaign_manager_id = fields.Many2one(
    'res.users',
    string="Responsable de campagne"
    )

    event_count = fields.Integer(
        string="Rendez-Vous",
        store=True,
        compute="_compute_counts"
    )

    attendee_count = fields.Integer(
        string="Nombre de RDV",
        compute="_compute_counts"
    )

    state = fields.Selection([
    ('draft', 'Brouillon'),
    ('open', 'Active'),
    ('expiring', 'À expirer bientôt'),
    ('closed', 'Fermée'),
       ], tracking=True, compute="_compute_state", store=True)
    

    monthly_rdv_volume = fields.Integer(
        string="Volume de RDV commandé / mois",store=True
    )

    rdv_carry_over = fields.Boolean(
        string="RDV reportables si non consommés"
    )

    price = fields.Monetary(
    string="Prix",
    currency_field='currency_id',
    groups="oui_allo_rdv_pro.group_call_admin"
)

    contract_attachment_ids = fields.Many2many(
    'ir.attachment',
    'campaign_attachment_rel',
    'campaign_id',
    'attachment_id',
    string="Contrats"
)


    currency_id = fields.Many2one(
        'res.currency',
        default=lambda self: self.env.company.currency_id
    )

    agenda_id = fields.Many2one(
        'resource.resource',
        string="Agenda affilié unique"
    )
    
    total_volume = fields.Integer(
    string="Volume total contractuel",
    compute="_compute_total_volume",
    store=True
    )
    rdv_realised = fields.Integer(
    string="RDV réalisés",
    compute="_compute_rdv_stats",
    store=True
    )

    rdv_remaining = fields.Integer(
        string="RDV restants",
        compute="_compute_rdv_stats",
        store=True
    )

    completion_rate = fields.Float(
    string="Taux de réalisation (%)",
    compute="_compute_completion_rate",
    store=True
    )

    invoice_id = fields.Many2one(
    'account.move',
    string="Facture",
    readonly=True,
    copy=False
    )
    rdv_month_count = fields.Integer('Rendez-Vous Mensuel', compute="_compute_rdv_month_count",store=True )

    invoice_count = fields.Integer(
        compute="_compute_invoice_count"
    )

    activity_id=fields.Many2one('activity.agence', 'Activité')

    date_start = fields.Date(string="Date de début", required=True)
    date_end = fields.Date(string="Date de fin", required=True)

    duration_months = fields.Integer(
    string="Durée calculée (mois)",
    compute="_compute_duration",
    store=True
)
    

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                delta = relativedelta(rec.date_end, rec.date_start)
                rec.duration_months = delta.years * 12 + delta.months + 1
            else:
                rec.duration_months = 0


    @api.constrains('date_start', 'date_end')
    def _check_dates(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                if rec.date_end < rec.date_start:
                    raise ValidationError("La date de fin doit être postérieure à la date de début.")


    def _compute_invoice_count(self):
        for rec in self:
            rec.invoice_count = 1 if rec.invoice_id else 0
    

    def action_view_invoice(self):
        self.ensure_one()

        # 1️⃣ Si facture existe déjà → ouvrir
        if self.invoice_id:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'account.move',
                'view_mode': 'form',
                'res_id': self.invoice_id.id,
            }

        # 2️⃣ Sinon → validations
        if not self.price:
            raise ValidationError("Le prix de la campagne est obligatoire.")

        if not self.client_id:
            raise ValidationError("Client obligatoire.")

        # 3️⃣ Création facture
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.client_id.id,
            'invoice_origin': self.name,
            'campaign_id': self.id,  # si champ ajouté dans account.move
            'invoice_line_ids': [(0, 0, {
                'name': f"Campagne {self.name}",
                'quantity': 1,
                'price_unit': self.price,
            })]
        })

        # 4️⃣ Lier à la campagne
        self.invoice_id = invoice.id

        # 5️⃣ Ouvrir facture créée
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': invoice.id,
        }


    @api.depends('rdv_realised', 'total_volume')
    def _compute_completion_rate(self):
        for rec in self:
            if rec.total_volume:
                rec.completion_rate = (rec.rdv_realised / rec.total_volume) * 100
            else:
                rec.completion_rate = 0

    @api.depends('date_start', 'date_end', 'monthly_rdv_volume')
    def _compute_total_volume(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                delta = relativedelta(rec.date_end, rec.date_start)
                months = delta.years * 12 + delta.months + 1
            else:
                months = 0

            rec.total_volume = months * (rec.monthly_rdv_volume or 0)


    # ------------------------
    # BOUTONS
    # ------------------------

    @api.constrains('duration_months', 'monthly_rdv_volume')
    def _check_positive_values(self):
        for rec in self:
            if rec.duration_months and rec.duration_months < 0:
                raise ValidationError("La durée ne peut pas être négative.")
            if rec.monthly_rdv_volume and rec.monthly_rdv_volume < 0:
                raise ValidationError("Le volume mensuel ne peut pas être négatif.")

    def action_close(self):
        self.write({'state': 'closed'})

    def action_reopen(self):
        self.write({'state': 'open'})

    # ------------------------
    # VALIDATION CLIENT
    # ------------------------

    @api.constrains('client_id')
    def _check_client_company(self):
        for rec in self:
            if rec.client_id and not rec.client_id.is_company:
                raise ValidationError("Le client doit être une société.")

    # ------------------------
    # SEQUENCE AUTOMATIQUE
    # ------------------------

    @api.model_create_multi
    def create(self, vals_list):

        for vals in vals_list:

            # Validation client obligatoire
            if not vals.get('client_id'):
                raise ValidationError(_("Le client est obligatoire."))

            if not vals.get('name') or vals.get('name') == '/':

                seq = self.env['ir.sequence'].next_by_code(
                    'oui.campaign'
                ) or '000'

                # 🔹 Client
                client_name = ""
                if vals.get('client_id'):
                    client = self.env['res.partner'].browse(
                        vals['client_id']
                    )
                    client_name = client.name or ""

                # 🔹 Activité
                activity_name = ""
                if vals.get('activity_id'):
                    activity = self.env['activity.agence'].browse(
                        vals['activity_id']
                    )
                    activity_name = activity.name or ""

                # 🔹 Date référence
                date_ref = vals.get('date_start') or fields.Date.today()
                date_obj = fields.Date.to_date(date_ref)

                month = date_obj.strftime("%B").capitalize()
                year = date_obj.strftime("%Y")
                day = date_obj.strftime("%d")

                # 🔹 Construction propre sans espaces inutiles
                parts = [
                    client_name,
                    activity_name,
                    f"{day} {month} {year}",
                    # seq
                ]

                vals['name'] = " - ".join([p for p in parts if p])

        return super().create(vals_list)



    # ------------------------
    # CREATION EVENEMENT
    # ------------------------

    def action_create_meeting(self):
        self.ensure_one()

        today = fields.Date.today()

        if self.state == 'closed':
            raise ValidationError("Impossible de créer un événement sur une campagne fermée.")

        if self.date_start and today < self.date_start:
            raise ValidationError("La campagne n'a pas encore commencé.")

        if self.date_end and today > self.date_end:
            raise ValidationError("La campagne est expirée.")

        event = self.env['calendar.event'].create({
            'name': self.name,
            'campaign_id': self.id,
            'start': fields.Datetime.now(),
            'stop': fields.Datetime.now(),
            'conseiller_id': self.campaign_manager_id.id or self.env.user.id,
        })

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'calendar.event',
            'view_mode': 'form',
            'res_id': event.id,
        }


    # ------------------------
    # COMPTEURS OPTIMISÉS
    # ------------------------
    @api.depends('attendee_ids.campaign_id')
    def _compute_counts(self):

        # Initialiser à 0 pour TOUS les records
        for rec in self:
            rec.event_count = 0

        # Filtrer seulement les records déjà sauvegardés
        saved_records = self.filtered(lambda r: r.id)

        if not saved_records:
            return

        event_data = self.env['calendar.event'].read_group(
            [('campaign_id', 'in', saved_records.ids)],
            ['campaign_id'],
            ['campaign_id']
        )

        mapped_events = {
            data['campaign_id'][0]: data['campaign_id_count']
            for data in event_data
        }

        for rec in saved_records:
            rec.event_count = mapped_events.get(rec.id, 0)




    # ------------------------
    # PROTECTION SI FERMÉE
    # ------------------------

    @api.depends('total_volume','attendee_ids.stage_id')
    def _compute_rdv_stats(self):

        if not self.ids:
            return

        # RDV réalisés (étape finale)
        realised_data = self.env['calendar.event'].read_group(
            [
                ('campaign_id', 'in', self.ids),
                ('stage_id.is_done', '=', True)
            ],
            ['campaign_id'],
            ['campaign_id']
        )

        realised_map = {
            data['campaign_id'][0]: data['campaign_id_count']
            for data in realised_data
        }

        for rec in self:
            realised = realised_map.get(rec.id, 0)
            rec.rdv_realised = realised
            rec.rdv_remaining = max(rec.total_volume - realised, 0)

    @api.depends('attendee_ids.start')
    def _compute_rdv_month_count(self):

        today = fields.Date.today()
        month_start = today.replace(day=1)
        month_end = month_start + relativedelta(months=1)

        data = self.env['calendar.event'].read_group(
            [
                ('campaign_id', 'in', self.ids),
                ('start', '>=', month_start),
                ('start', '<', month_end),
            ],
            ['campaign_id'],
            ['campaign_id']
        )

        month_map = {
            d['campaign_id'][0]: d['campaign_id_count']
            for d in data
        }

        for rec in self:
            rec.rdv_month_count = month_map.get(rec.id, 0)



    def write(self, vals):
        if not self.env.context.get('bypass_state_lock'):
            for rec in self:
                if rec.state == 'closed' and any(
                    key not in ['state', 'message_follower_ids']
                    for key in vals.keys()
                ):
                    raise ValidationError("Impossible de modifier une campagne fermée.")

        return super().write(vals)

    
    @api.depends('date_start', 'date_end')
    def _compute_state(self):
        today = fields.Date.today()

        for rec in self:
            if not rec.date_start or not rec.date_end:
                rec.state = 'draft'
                continue

            if today < rec.date_start:
                rec.state = 'draft'
            elif rec.date_start <= today <= rec.date_end:
                # campagne active
                days_left = (rec.date_end - today).days
                if days_left <= 7:
                    rec.state = 'expiring'
                else:
                    rec.state = 'open'
            else:
                rec.state = 'closed'
    
    def action_open_generate_rdv_wizard(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Générer RDV',
            'res_model': 'campaign.generate.rdv.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_campaign_id': self.id,
                'default_partner_id': self.client_id.id,
                'default_responsable_id': self.campaign_manager_id.id,
                'default_conseiller_ids': [(6, 0, self.conseiller_ids.ids)],
                'default_rdv_line_ids.conseiller_ids': [(6, 0, self.conseiller_ids.ids)],

            }
        }
    
    def action_view_realised(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'RDV Réalisés',
            'res_model': 'calendar.event',
            'view_mode': 'list,kanban,form,calendar',
            'domain': [
                ('campaign_id', '=', self.id),
                ('stage_id.is_done', '=', True)
            ],
        }
    
    def action_view_agenda(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'AGENDA',
            'res_model': 'calendar.event',
            'view_mode': 'calendar',
            'domain': [
                ('campaign_id', '=', self.id) ],
        }
    def action_view_campagne_evens(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Campagne RDV',
            'res_model': 'calendar.event',
            'view_mode': 'kanban,list,form,calendar',
            'domain': [
                ('campaign_id', '=', self.id) ],
        }
    
    @api.model
    def get_executive_dashboard_data(self, period='month'):
        """Retourne les données du dashboard exécutif pour une période donnée"""

        today = fields.Date.today()
        start_date = today
        end_date = today

        # Déterminer la période
        if period == 'week':
            start_date = today - timedelta(days=today.weekday())  # lundi de la semaine
            end_date = start_date + timedelta(days=6)
        elif period == 'month':
            start_date = today.replace(day=1)
            end_date = start_date + relativedelta(months=1, days=-1)
        elif period == 'quarter':
            quarter = (today.month - 1) // 3 + 1
            start_date = datetime(today.year, 3*quarter-2, 1).date()
            end_date = start_date + relativedelta(months=3, days=-1)
        elif period == 'year':
            start_date = datetime(today.year, 1, 1).date()
            end_date = datetime(today.year, 12, 31).date()

        # Filtrer les RDV sur la période
        Event = self.env['calendar.event']
        events = Event.search([('start', '>=', start_date), ('start', '<=', end_date)])

        # KPI globaux
        total_rdv = len(events)
        exploite_rdv = len(events.filtered(lambda e: e.stage_id.is_done))
        absent_rdv = len(events.filtered(lambda e: e.stage_id.name == 'Absent'))
        taux_exploitation = (exploite_rdv / total_rdv * 100) if total_rdv else 0

        global_data = {
            'total': total_rdv,
            'exploite': exploite_rdv,
            'absent': absent_rdv,
            'taux_exploitation': taux_exploitation,
        }

        # KPI par conseiller
        conseillers = self.env['res.users'].search([('share', '=', False)])  # tous les conseillers
        conseillers_data = []

        for c in conseillers:
            c_events = events.filtered(lambda e: c.id in e.conseiller_id.ids)
            pris = len(c_events)
            exploite = len(c_events.filtered(lambda e: e.stage_id.is_done))
            absent = len(c_events.filtered(lambda e: e.stage_id.name == 'Absent'))
            taux = (exploite / pris * 100) if pris else 0
            objectif = ((end_date - start_date).days // 3) * 2  # 2 RDV tous les 3 jours
            objectif_atteint = pris >= objectif

            conseillers_data.append({
                'id': c.id,
                'name': c.name,
                'pris': pris,
                'exploite': exploite,
                'absent': absent,
                'taux_exploitation': taux,
                'objectif': objectif,
                'objectif_atteint': objectif_atteint,
            })

        # KPI par campagne
        campagnes = self.search([('date_start', '<=', end_date), ('date_end', '>=', start_date)])
        campagnes_data = []

        is_admin = self.env.user.has_group('oui_allo_rdv_pro.group_call_admin')

        for camp in campagnes:
            camp_events = events.filtered(lambda e: e.campaign_id.id == camp.id)
            commande = camp.monthly_rdv_volume
            pris = len(camp_events)
            exploite = len(camp_events.filtered(lambda e: e.stage_id.is_done))
            absent = len(camp_events.filtered(lambda e: e.stage_id.name == 'Absent'))
            reporte = len(camp_events.filtered(lambda e: e.stage_id.name == 'Reporté'))
            restant = max(commande - pris, 0)
            taux = (exploite / pris * 100) if pris else 0

            # Conseillers stats
            conseillers_camp = []
            for c in camp.conseiller_ids:
                c_ev = camp_events.filtered(lambda e: c.id in e.conseiller_id.ids)
                c_pris = len(c_ev)
                c_exploite = len(c_ev.filtered(lambda e: e.stage_id.is_done))
                c_taux = (c_exploite / c_pris * 100) if c_pris else 0
                conseillers_camp.append({
                    'id': c.id,
                    'name': c.name,
                    'pris': c_pris,
                    'exploite': c_exploite,
                    'taux': c_taux,
                })

            campagnes_data.append({
                'id': camp.id,
                'name': camp.name,
                'commande': commande,
                'pris': pris,
                'exploite': exploite,
                'absent': absent,
                'reporte': reporte,
                'restant': restant,
                'taux_exploitation': taux,
                'price_paid': camp.price if is_admin else 0,
                'conseillers': conseillers_camp,
            })

        return {
            'global': global_data,
            'conseillers': conseillers_data,
            'campagnes': campagnes_data,
            'is_admin': is_admin,
        }

class AccountMove(models.Model):
    _inherit = 'account.move'

    campaign_id = fields.Many2one(
        'oui.campaign',
        string="Campagne"
    )