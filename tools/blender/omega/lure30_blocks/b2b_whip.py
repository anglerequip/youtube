    elif mv[0] == 'whip':                                       # whip-pan: from the speaker to the window in ~0.3 s
        d0 = (Vector(mv[1]) - loc).normalized(); d1 = (tgt - loc).normalized()
        for f in range(f0, f1 + 1):
            u = min(1.0, (f - f0) / 7.0); u = u * u * (3 - 2 * u)
            dd = d0.lerp(d1, u).normalized()
            c.rotation_euler = dd.to_track_quat('-Z', 'Y').to_euler(); c.keyframe_insert('rotation_euler', frame=f)
            c.location = loc + (tgt - loc) * 0.05 * max(0.0, (f - f0 - 7) / max(1, f1 - f0 - 7)); c.keyframe_insert('location', frame=f)
