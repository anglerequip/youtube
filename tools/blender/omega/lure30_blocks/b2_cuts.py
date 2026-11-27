PH = Vector((0.15, -0.8, 1.3))                                             # the phone insert, staged on its own
tpl('burst', (0.5, -1.6, 1.0), (0.05, -0.05, 0.62), 22, 6.0)
tpl('boots', tuple(NF_ + Vector((0.6, -0.95, 0.2))), tuple(NF_ + Vector((-0.15, -0.05, 0.12))), 24, 3.2)
tpl('window', (0.0, -0.35, 1.45), (0.0, D1 + 0.5, 1.5), 30, 8.0)
tpl('phone', tuple(PH + Vector((0.02, -0.24, 0.02))), tuple(PH), 50, 2.2)
tpl('float', (0.5, -1.25, 0.8), (0.12, -0.08, 0.62), 30, 4.0)
T_OUT = word_t(4, 'outside') - 0.12
T_PRES = word_t(5, 'Pressure') - 0.15
cuts = [(0.0, 'burst', ('creep', 0.06)),
        (1.95, 'boots', ('creep', 0.15)),
        (3.25, 'nils', ('punch', word_t(2, 'lake') - 0.1, 1.3)),
        (ts(3) - 0.15, 'theo', ('punch', word_t(3, 'which') - 0.05, 1.2)),
        (ts(4) - 0.15, 'nils', ('creep', 0.05)),
        (T_OUT, 'window', ('whip', H_N)),
        (T_PRES, 'baro', ('rack', 0.25)),
        (ts(6) - 0.1, 'hero', ('creep', 0.16)),
        (ts(7) - 0.1, 'theo', ('punch', word_t(7, 'window') - 0.1, 1.3)),
        (ts(8) - 0.1, 'two', ('creep', 0.06)),
        (word_t(8, 'asked') - 0.1, 'nils', ('punch', word_t(8, 'AnglerMind') - 0.05, 1.35)),
        (ts(9) - 0.1, 'phone', ('creep', 0.2)),
        (22.55, 'float', ('creep', 0.08)),
        (ts(10) - 0.1, 'theo', ('creep', 0.06)),
        (ts(11) - 0.1, 'ecu', ('punch', word_t(11, 'presents') - 0.05, 1.2)),
        (ts(12) - 0.1, 'hero', ('creep', 0.08))]
