def post_init_hook(env):
    """Activa module_pos_hr en todas las configuraciones de POS existentes."""
    pos_configs = env['pos.config'].search([])
    if pos_configs:
        pos_configs.write({'module_pos_hr': True})
