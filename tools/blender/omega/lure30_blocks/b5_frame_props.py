    # ---------------------------------------------------------------- props that follow hands, the hero lure, the weather
    bpy.context.view_layer.update()
    for who_, a_ in rig.items():                                    # feet stay on the floor (mocap bends knees, hips don't drop)
        az = min((a_.matrix_world @ a_.pose.bones[b_].tail).z for b_ in ('shin.L', 'shin.R'))
        a_.location.z += ANK0[who_] - az; a_.keyframe_insert('location', index=2, frame=f)
    bpy.context.view_layer.update()
    def tail(who, b): return rig[who].matrix_world @ rig[who].pose.bones[b].tail
    def ss(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)
    hl = tail('nils', 'hand.L'); hz = hl.z
    tilt = ss((hz - 1.2) / 0.25) * math.radians(75)
    v_ = (H_N - hl); ax = Vector((0, 0, 1)).cross(Vector((v_.x, v_.y, 0)))
    qm = Quaternion(ax.normalized(), tilt) if ax.length > 1e-6 else Quaternion()
    MUG.rotation_mode = 'QUATERNION'; MUG.rotation_quaternion = qm @ Quaternion((0, 0, 1), nils.rotation_euler.z)
    MUG.location = hl + qm @ Vector((0, 0, -0.045)); MUG.keyframe_insert('location', frame=f); MUG.keyframe_insert('rotation_quaternion', frame=f)
    # phone in Nils's right hand, screen toward Theo
    PHONE.rotation_mode = 'QUATERNION'
    if ts(8) + 0.15 <= t <= 24.75:
        hr = tail('nils', 'hand.R'); PHONE.location = hr + Vector((0, 0, 0.05))
        PHONE.rotation_quaternion = (H_T - hr).normalized().to_track_quat('-Y', 'Z')
    else:
        PHONE.location = (0, 0, -5)
    PHONE.keyframe_insert('location', frame=f); PHONE.keyframe_insert('rotation_quaternion', frame=f)
    # the phone insert, held in its own space with a little hand drift; its pin pulses
    if ts(9) - 0.2 <= t <= 22.6:
        PHONE_HERO.location = PH + Vector((0.004 * math.sin(t * 1.3), 0, 0.003 * math.sin(t * 1.7)))
        PHONE_HERO.rotation_euler = (math.radians(4 + 1.0 * math.sin(t * 0.9)), math.radians(-3), math.radians(2 * math.sin(t * 0.7)))
        u_ = ((t - ts(9)) % 1.0)
        mw_ = Matrix.Translation(PHONE_HERO.location) @ PHONE_HERO.rotation_euler.to_matrix().to_4x4()
        PULSE.location = mw_ @ Vector((0.01, -0.0065, 0.024))   # the pin on the screen image
        PULSE.rotation_euler = PHONE_HERO.rotation_euler.copy(); PULSE.rotation_euler.x += math.radians(90)
        sc_ = 0.4 + 1.1 * u_; PULSE.scale = (sc_, sc_, 1)
    else:
        PHONE_HERO.location = (0, 0, -5); PULSE.location = (0, 0, -6)
    for o_ in (PHONE_HERO, PULSE):
        o_.keyframe_insert('location', frame=f); o_.keyframe_insert('rotation_euler', frame=f)
    PULSE.keyframe_insert('scale', frame=f)
    # Theo's two lures
    for o_, s_ in zip(HL, 'LR'):
        if ts(3) - 0.25 <= t <= ts(3) + 1.8:
            o_.location = tail('theo', 'hand.' + s_) + Vector((0, 0, 0.01)); o_.rotation_euler = (0, math.radians(12 if s_ == 'L' else -12), 0)
        else:
            o_.location = (0, 0, -5)
        o_.keyframe_insert('location', frame=f); o_.keyframe_insert('rotation_euler', frame=f)
    # the hero lure
    HERO.rotation_mode = 'XYZ'; glow = 0.0
    yaw_ = 0.7
    if t < 0.9:
        HERO.location = BOXP + Vector((0, 0, 0.2)); HERO.rotation_euler = (0, 0, 0)
    elif t < 1.55:
        u_ = (t - 0.9) / 0.65; p0 = BOXP + Vector((0, 0, 0.32))
        HERO.location = p0.lerp(HERO_START, u_) + Vector((0, 0, 0.55 * math.sin(math.pi * u_) * (1 - u_ * 0.3)))
        HERO.rotation_euler = (math.radians(90) * u_ + 6 * u_ * (1 - u_), 0, yaw_)
    elif t < 22.6:
        HERO.location = HERO_START; HERO.rotation_euler = (math.radians(90), 0, yaw_)
    elif t < 23.4:
        u_ = ss((t - 22.6) / 0.8); HERO.location = HERO_START + Vector((0, 0, 0.45 * u_))
        HERO.rotation_euler = (math.radians(90 - 70 * u_), 0, yaw_ + 2.5 * u_); glow = 5.0 * u_
    elif t < 24.3:
        u_ = ss((t - 23.4) / 0.9); top = HERO_START + Vector((0, 0, 0.45)); hand = tail('theo', 'hand.L') + Vector((0, 0, 0.05))
        HERO.location = top.lerp(hand, u_) + Vector((0, 0, 0.12 * math.sin(math.pi * u_) + 0.015 * math.sin(t * 9)))
        HERO.rotation_euler = (math.radians(20), 0, yaw_ + 2.5 + 3.0 * u_); glow = 5.0
    else:
        HERO.location = tail('theo', 'hand.L') + Vector((0, 0, 0.05)); HERO.rotation_euler = (math.radians(20), 0, yaw_ + 5.5)
        glow = 5.0 - 4.0 * ss((t - 24.3) / 1.2)
    HERO.keyframe_insert('location', frame=f); HERO.keyframe_insert('rotation_euler', frame=f)
    _hb.inputs['Emission Strength'].default_value = glow; _hb.inputs['Emission Strength'].keyframe_insert('default_value', frame=f)
    HERO_HALO.location = HERO.location if glow > 0 else Vector((0, 0, -5)); HERO_HALO.data.energy = 3.0 * glow
    HERO_HALO.keyframe_insert('location', frame=f); HERO_HALO.data.keyframe_insert('energy', frame=f)
    # weather: clouds roll in, the trees start to bend, the sun goes in
    if f % 2 == 1 or f == N:
        tw = ss((t - 8.4) / 1.6)
        smp.inputs['Location'].default_value = (0.03 * t + 0.35 * max(0.0, t - 8.4), 0, 0); smp.inputs['Location'].keyframe_insert('default_value', frame=f)
        sgrey.inputs['Factor'].default_value = 0.7 * tw; sgrey.inputs['Factor'].keyframe_insert('default_value', frame=f)
        SUN.data.energy = 4.5 * (1 - 0.45 * tw); SUN.data.keyframe_insert('energy', frame=f)
        amp = 0.015 + 0.09 * tw + 0.06 * tw * max(0.0, math.sin(t * 2.1))
        for k_, o_ in enumerate(BUSHES):
            r0 = o_['r0']; o_.rotation_euler = (r0[0] + amp * math.sin(t * 2.3 + k_), r0[1] + amp * 0.8 * math.sin(t * 1.9 + 2 * k_), r0[2])
            o_.keyframe_insert('rotation_euler', frame=f)
    # the barometer needle falls from FAIR toward RAIN on "pressure falling"
    tn = T_PRES + 0.15
    ang = 40.0 if t < tn else 40.0 - 82.0 * (1 - (1 - min(1.0, (t - tn) / 1.1)) ** 3) + 3.0 * math.exp(-3 * max(0, t - tn - 1.1)) * math.sin(14 * max(0, t - tn - 1.1))
    needle.rotation_euler = (0, math.radians(ang), 0); needle.keyframe_insert('rotation_euler', frame=f)
