import math

def calculate_fwi(temp, rh, wind, rain, prev_ffmc=85.0, prev_dmc=6.0, prev_dc=15.0):
    """
    Calculates the Canadian Forest Fire Weather Index (FWI) System components.
    Based on the mathematical equations by Van Wagner (1987).
    """
    
    # ----------------------------------------------------
    # 1. Fine Fuel Moisture Code (FFMC)
    # ----------------------------------------------------
    mo = 147.2 * (101.0 - prev_ffmc) / (59.5 + prev_ffmc)
    
    if rain > 0.5:
        rf = rain - 0.5
        if mo > 150.0:
            mo = (mo + 42.5 * rf * math.exp(-100.0 / (251.0 - mo)) * 
                  (1.0 - math.exp(-6.93 / rf)))
        else:
            mo = mo + 42.5 * rf * math.exp(-100.0 / (251.0 - mo)) * (1.0 - math.exp(-6.93 / rf))
        if mo > 250.0:
            mo = 250.0

    ed = 0.942 * math.pow(rh, 0.679) + 11.0 * math.exp((rh - 100.0) / 10.0) + 0.18 * (21.1 - temp) * (1.0 - math.exp(-0.115 * rh))
    
    if mo < ed:
        ew = 0.618 * math.pow(rh, 0.753) + 10.0 * math.exp((rh - 100.0) / 10.0) + 0.18 * (21.1 - temp) * (1.0 - math.exp(-0.115 * rh))
        if mo <= ew:
            kl = 0.424 * (1.0 - math.pow(rh / 100.0, 1.7)) + 0.0694 * math.sqrt(wind) * (1.0 - math.pow(rh / 100.0, 8))
            kw = kl * 0.581 * math.exp(0.0365 * temp)
            m = ew - (ew - mo) * math.pow(10.0, -kw)
        else:
            m = mo
    else:
        kl = 0.424 * (1.0 - math.pow(rh / 100.0, 1.7)) + 0.0694 * math.sqrt(wind) * (1.0 - math.pow(rh / 100.0, 8))
        kw = kl * 0.581 * math.exp(0.0365 * temp)
        m = ed + (mo - ed) * math.pow(10.0, -kw)
        
    ffmc = (59.5 * (250.0 - m)) / (147.2 + m)
    if ffmc > 101.0: ffmc = 101.0
    if ffmc < 0.0: ffmc = 0.0

    # ----------------------------------------------------
    # 2. Duff Moisture Code (DMC)
    # ----------------------------------------------------
    t = temp if temp >= -1.1 else -1.1

    if rain > 1.5:
        re = 0.92 * rain - 1.27
        mo_dmc = 20.0 + math.exp(5.6348 - prev_dmc / 43.43)
        
        if prev_dmc <= 33.0:
            b = 100.0 / (0.5 + 0.3 * prev_dmc)
        elif prev_dmc <= 65.0:
            b = 14.0 - 1.3 * math.log(prev_dmc)
        else:
            b = 6.2 * math.log(prev_dmc) - 17.2
            
        mr_dmc = mo_dmc + 1000.0 * re / (48.77 + b * re)
        pr_dmc = 244.72 - 43.43 * math.log(mr_dmc - 20.0)
        
        if pr_dmc < 0.0: pr_dmc = 0.0
    else:
        pr_dmc = prev_dmc

    if rh < 100.0:
        # Without a specific month passed to the function, 
        # we assume a standard mid-summer effective day length (dl = 9.0)
        dl = 9.0 
        k_dmc = 1.894 * (t + 1.1) * (100.0 - rh) * dl * 1e-6
    else:
        k_dmc = 0.0

    dmc = pr_dmc + 100.0 * k_dmc
    if dmc < 0.0: dmc = 0.0

    # ----------------------------------------------------
    # 3. Drought Code (DC)
    # ----------------------------------------------------
    t_dc = temp if temp >= -2.8 else -2.8

    if rain > 2.8:
        rd = 0.83 * rain - 1.27
        sma = 0.36 * prev_dc + 0.04
        mr_dc = sma + 3.937 * rd
        pr_dc = 400.0 * math.log(800.0 / mr_dc)
        if pr_dc < 0.0: pr_dc = 0.0
    else:
        pr_dc = prev_dc

    # Standard mid-summer day length factor for DC
    fl = 1.4 
    v = 0.36 * (t_dc + 2.8) + fl
    if v < 0.0: v = 0.0

    dc = pr_dc + 0.5 * v
    if dc < 0.0: dc = 0.0

    # ----------------------------------------------------
    # 4. Initial Spread Index (ISI)
    # ----------------------------------------------------
    mo_ffmc = 147.2 * (101.0 - ffmc) / (59.5 + ffmc)
    fw = math.exp(0.05039 * wind)
    ff = 91.9 * math.exp(-0.1386 * mo_ffmc) * (1.0 + math.pow(mo_ffmc, 5.31) / 4.93e7)
    isi = 0.208 * fw * ff

    # ----------------------------------------------------
    # 5. Buildup Index (BUI)
    # ----------------------------------------------------
    if dmc <= 0.4 * dc:
        bui = 0.8 * dc * dmc / (dmc + 0.4 * dc)
    else:
        bui = dmc - (1.0 - 0.8 * dc / (dmc + 0.4 * dc)) * (0.92 + math.pow(0.0114 * dmc, 1.7))
        
    if bui < 0.0: bui = 0.0

    # ----------------------------------------------------
    # 6. Fire Weather Index (FWI)
    # ----------------------------------------------------
    if bui <= 80.0:
        bb = 0.1 * isi * (0.626 * math.pow(bui, 0.809) + 2.0)
    else:
        bb = 0.1 * isi * (1000.0 / (25.0 + 108.64 * math.exp(-0.023 * bui)))
        
    if bb <= 1.0:
        fwi = bb
    else:
        fwi = math.exp(2.72 * math.pow(0.434 * math.log(bb), 0.647))

    return {
        "FFMC": round(ffmc, 2),
        "DMC": round(dmc, 2),
        "DC": round(dc, 2),
        "ISI": round(isi, 2),
        "BUI": round(bui, 2),
        "FWI": round(fwi, 2)
    }
