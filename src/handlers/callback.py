    elif callback_data == "first_buyers":
        await handle_first_buyers(update, context)
    elif callback_data == "ath_market_cap":
        await handle_ath_market_cap(update, context)
    elif callback_data == "scan_wallet":
        await handle_scan_wallet(update, context)
    elif callback_data == "top_holders":
        await handle_top_holders(update, context)
    elif callback_data == "profitable_wallets":
        await handle_profitable_wallets(update, context)
    elif callback_data == "high_net_worth":
        await handle_high_net_worth(update, context)
    elif callback_data == "track_wallet_trades":
        await handle_track_wallet_trades(update, context)
    elif callback_data == "track_wallet_deployments":
        await handle_track_wallet_deployments(update, context)
    elif callback_data == "deployer_wallet_scan":
        await handle_deployer_wallet_scan(update, context)
    elif callback_data == "track_whale_sales":
        await handle_track_whale_sales(update, context)
    elif callback_data.startswith("more_buyers_"):
        token_address = callback_data.replace("more_buyers_", "")
        await handle_more_buyers(update, context, token_address)
    elif callback_data == "more_kols":
        await handle_more_kols(update, context)
    elif callback_data.startswith("export_td_"):
        wallet_address = callback_data.replace("export_td_", "")
        await handle_export_td(update, context, wallet_address)
    elif callback_data.startswith("export_th_"):
        token_address = callback_data.replace("export_th_", "")
        await handle_export_th(update, context, token_address)
    elif callback_data == "export_pw":
        await handle_export_pw(update, context)
    elif callback_data == "export_hnw":
        await handle_export_hnw(update, context)
    elif callback_data.startswith("track_deployer_"):
        deployer_address = callback_data.replace("track_deployer_", "")
        await handle_track_deployer(update, context, deployer_address)
    elif callback_data == "track_top_wallets":
        await handle_track_top_wallets(update, context)
    elif callback_data == "track_hnw_wallets":
        await handle_track_hnw_wallets(update, context)
    elif callback_data.startswith("th_"):
        token_address = callback_data.replace("th_", "")
        await handle_th(update, context, token_address)
    elif callback_data.startswith("dw_"):
        token_address = callback_data.replace("dw_", "")
        await handle_dw(update, context, token_address)
    elif callback_data.startswith("track_token_"):
        token_address = callback_data.replace("track_token_", "")
        await handle_track_token(update, context, token_address)
    elif callback_data.startswith("track_wallet_"):
        wallet_address = callback_data.replace("track_wallet_", "")
        await handle_track_wallet(update, context, wallet_address)
    elif callback_data.startswith("trading_history_"):
        wallet_address = callback_data.replace("trading_history_", "")
        await handle_trading_history(update, context, wallet_address)
    elif callback_data.startswith("more_history_"):
        wallet_address = callback_data.replace("more_history_", "")
        await handle_more_history(update, context, wallet_address)
    elif callback_data.startswith("export_ptd"):
        await handle_export_ptd(update, context)
    elif callback_data.startswith("export_mpw_"):
        token_address = callback_data.replace("export_mpw_", "")
        await handle_export_mpw(update, context, token_address)
    else:
        # Unknown callback data
        await query.answer(
            "Sorry, I couldn't process that request. Please try again.", show_alert=True
        )