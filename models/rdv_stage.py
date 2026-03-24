
from odoo import models, fields

class RdvStage(models.Model):
    _name = 'rdv.stage'
    _description = 'Pipeline RDV'
    _order = 'sequence'

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    fold = fields.Boolean(string="Replié")
    color = fields.Integer("Couleur")
    is_done = fields.Boolean(string="Étape finale")

class AgenceActivity(models.Model):
    _name = 'activity.agence'
    _description = 'Acticity Agence'

    name=fields.Char('Activité')


