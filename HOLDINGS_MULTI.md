# Holding View Tab for Multi-portfolio 

## Small issues
 - Please start on the graph view instead of the tabular view 
 - All portfolios in the database should be selected initially when the app opens, if the user changes a setting, please persist that until the app is closed
 - When changing the portfolio selection make sure the total value of the holdings is updated  

## Graph View
There are still issues with the graph view.  Can you examine the code and make sure everything is correct?  I will try
to describe the issues i'm seeing.  
 - The graph doesn't seem to have all the portfolios in it.
 - Switching to graph view loads the graph, but then it seems to switch back to the tabular view -- without switching
 the radio button.  

 Here is the log from the console: 

```
For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
INFO:pagr.portfolio_manager:Listed 2 portfolios from database: [{'name': 'muti-asset_portfolio', 'created_at': '2025-12-05T09:08:57.059364', 'position_count': 21}, {'name': 'sample_portfolio', 'created_at': '2025-12-05T11:38:22.255542', 'position_count': 5}]
INFO:pagr.ui.tab_portfolio_selection:Refreshed portfolio list from database: 2 portfolios found
INFO:pagr.portfolio_analysis_service:Initialized PortfolioAnalysisService
INFO:pagr.portfolio_manager:Listed 2 portfolios from database: [{'name': 'muti-asset_portfolio', 'created_at': '2025-12-05T09:08:57.059364', 'position_count': 21}, {'name': 'sample_portfolio', 'created_at': '2025-12-05T11:38:22.255542', 'position_count': 5}]
INFO:pagr.portfolio_loader:Available portfolios: ['muti-asset_portfolio', 'sample_portfolio']
INFO:pagr.ui.tab_holdings:Available portfolios in Holdings View: ['muti-asset_portfolio', 'sample_portfolio']
INFO:pagr.portfolio_manager:Starting reconstruction of portfolio: muti-asset_portfolio
INFO:pagr.portfolio_manager:Reconstructed portfolio 'muti-asset_portfolio' with 21 positions from database
INFO:pagr.portfolio_loader:Loaded portfolio: muti-asset_portfolio (21 positions)
INFO:pagr.ui.tab_holdings:Loaded 1 portfolios from database
INFO:pagr.ui.tab_holdings:Display portfolios: ['muti-asset_portfolio'], total positions: 21
INFO:pagr.portfolio_analysis_service:Initialized PortfolioAnalysisService
INFO:pagr.ui.components.portfolio_selector:Portfolio selection changed to: ['muti-asset_portfolio', 'sample_portfolio']
INFO:pagr.portfolio_manager:Listed 2 portfolios from database: [{'name': 'muti-asset_portfolio', 'created_at': '2025-12-05T09:08:57.059364', 'position_count': 21}, {'name': 'sample_portfolio', 'created_at': '2025-12-05T11:38:22.255542', 'position_count': 5}]
INFO:pagr.ui.tab_portfolio_selection:Refreshed portfolio list from database: 2 portfolios found
INFO:pagr.portfolio_analysis_service:Initialized PortfolioAnalysisService
INFO:pagr.portfolio_manager:Listed 2 portfolios from database: [{'name': 'muti-asset_portfolio', 'created_at': '2025-12-05T09:08:57.059364', 'position_count': 21}, {'name': 'sample_portfolio', 'created_at': '2025-12-05T11:38:22.255542', 'position_count': 5}]
INFO:pagr.portfolio_loader:Available portfolios: ['muti-asset_portfolio', 'sample_portfolio']
INFO:pagr.ui.tab_holdings:Available portfolios in Holdings View: ['muti-asset_portfolio', 'sample_portfolio']
INFO:pagr.ui.components.portfolio_selector:Portfolio selection changed to: ['muti-asset_portfolio']
INFO:pagr.portfolio_manager:Listed 2 portfolios from database: [{'name': 'muti-asset_portfolio', 'created_at': '2025-12-05T09:08:57.059364', 'position_count': 21}, {'name': 'sample_portfolio', 'created_at': '2025-12-05T11:38:22.255542', 'position_count': 5}]
INFO:pagr.ui.tab_portfolio_selection:Refreshed portfolio list from database: 2 portfolios found
INFO:pagr.portfolio_analysis_service:Initialized PortfolioAnalysisService
INFO:pagr.portfolio_manager:Listed 2 portfolios from database: [{'name': 'muti-asset_portfolio', 'created_at': '2025-12-05T09:08:57.059364', 'position_count': 21}, {'name': 'sample_portfolio', 'created_at': '2025-12-05T11:38:22.255542', 'position_count': 5}]
INFO:pagr.portfolio_loader:Available portfolios: ['muti-asset_portfolio', 'sample_portfolio']
INFO:pagr.ui.tab_holdings:Available portfolios in Holdings View: ['muti-asset_portfolio', 'sample_portfolio']
INFO:pagr.portfolio_manager:Starting reconstruction of portfolio: muti-asset_portfolio
INFO:pagr.portfolio_manager:Reconstructed portfolio 'muti-asset_portfolio' with 21 positions from database
INFO:pagr.portfolio_loader:Loaded portfolio: muti-asset_portfolio (21 positions)
INFO:pagr.ui.tab_holdings:Loaded 1 portfolios from database
INFO:pagr.ui.tab_holdings:Display portfolios: ['muti-asset_portfolio'], total positions: 21
2025-12-05 11:42:22.099 Please replace `use_container_width` with `width`.

`use_container_width` will be removed after 2025-12-31.

For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
2025-12-05 11:42:22.111 Please replace `use_container_width` with `width`.

`use_container_width` will be removed after 2025-12-31.

For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
2025-12-05 11:42:22.151 Please replace `use_container_width` with `width`.

`use_container_width` will be removed after 2025-12-31.

For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
2025-12-05 11:42:22.167 Please replace `use_container_width` with `width`.

`use_container_width` will be removed after 2025-12-31.

For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
2025-12-05 11:42:22.204 Please replace `use_container_width` with `width`.

`use_container_width` will be removed after 2025-12-31.

For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
2025-12-05 11:42:22.218 Please replace `use_container_width` with `width`.

`use_container_width` will be removed after 2025-12-31.

For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
2025-12-05 11:42:22.257 Please replace `use_container_width` with `width`.

`use_container_width` will be removed after 2025-12-31.

For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
2025-12-05 11:42:22.269 Please replace `use_container_width` with `width`.

`use_container_width` will be removed after 2025-12-31.

For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
2025-12-05 11:42:22.310 Please replace `use_container_width` with `width`.

`use_container_width` will be removed after 2025-12-31.

For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
INFO:pagr.portfolio_analysis_service:Initialized PortfolioAnalysisService
2025-12-05 11:42:22.338 Please replace `use_container_width` with `width`.

`use_container_width` will be removed after 2025-12-31.

For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
2025-12-05 11:42:22.375 Please replace `use_container_width` with `width`.

`use_container_width` will be removed after 2025-12-31.

For `use_container_width=True`, use `width='stretch'`. For `use_container_width=False`, use `width='content'`.
```


