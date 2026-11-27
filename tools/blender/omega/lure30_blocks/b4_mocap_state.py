    def mocap_state(who, t):
        talking_ = any(s_ - 0.15 <= t <= e_ + 0.3 for (w_, s_, e_, _) in speaking if w_ == who)
        if who == 'theo' and t < 0.75:
            return ('Chest_Open', t + 0.35)                          # already bent over the latches on frame 1
        if who == 'nils' and 2.95 <= t < 4.0:
            return ('Consume', t - 2.95)                             # a slow sip, looking at the lures
        if who == 'nils' and 27.8 <= t < 28.85:
            return ('Consume', t - 27.8)                             # "Christmas presents." ... sip
        return ('Idle_Talking_Loop' if talking_ else 'Idle_Loop', t + MOFS[who])
