"""Portfolio loading service with caching and multi-portfolio support."""

import logging
from typing import List, Optional, Dict
from pagr.portfolio_manager import PortfolioManager
from pagr.session_manager import SessionManager
from pagr.fds.models.portfolio import Portfolio

logger = logging.getLogger(__name__)


class PortfolioLoader:
    """Handles efficient loading and reconstruction of portfolios from database.

    This service centralizes portfolio loading logic and provides caching
    to avoid redundant database queries when the same portfolios are requested
    multiple times in the same session.
    """

    def __init__(self, portfolio_manager: PortfolioManager):
        """Initialize portfolio loader.

        Args:
            portfolio_manager: PortfolioManager instance for database operations
        """
        self.portfolio_manager = portfolio_manager
        self._cache: Dict[str, Portfolio] = {}

    def get_available_portfolios(self, force_refresh: bool = False) -> List[Dict]:
        """Get list of all available portfolios from database.

        Updates session state with available portfolios.

        Args:
            force_refresh: If True, bypass cache and query database

        Returns:
            List of portfolio dicts with keys: name, created_at, position_count
        """
        try:
            if force_refresh:
                logger.debug("Force refreshing portfolio list from database")
                portfolios = self.portfolio_manager.list_portfolios()
            else:
                available = SessionManager.get_available_portfolios()
                if available:
                    logger.debug(f"Using cached portfolio list: {len(available)} portfolios")
                    return available

                logger.debug("Cache miss, querying database for portfolios")
                portfolios = self.portfolio_manager.list_portfolios()

            if portfolios:
                SessionManager.set_available_portfolios(portfolios)
                logger.info(f"Available portfolios: {[p.get('name') for p in portfolios]}")
            else:
                logger.warning("No portfolios found in database")

            return portfolios

        except Exception as e:
            logger.error(f"Failed to get available portfolios: {e}")
            return []

    def load_portfolio(self, portfolio_name: str) -> Optional[Portfolio]:
        """Load a single portfolio with caching.

        Args:
            portfolio_name: Name of portfolio to load

        Returns:
            Portfolio object or None if not found
        """
        # Check cache first
        if portfolio_name in self._cache:
            logger.debug(f"Cache hit for portfolio: {portfolio_name}")
            return self._cache[portfolio_name]

        # Reconstruct from database
        logger.debug(f"Loading portfolio from database: {portfolio_name}")
        portfolio = self.portfolio_manager.reconstruct_portfolio_from_database(portfolio_name)

        if portfolio:
            self._cache[portfolio_name] = portfolio
            logger.info(f"Loaded portfolio: {portfolio_name} ({len(portfolio.positions)} positions)")

        return portfolio

    def load_portfolios(self, portfolio_names: List[str]) -> List[Portfolio]:
        """Load multiple portfolios efficiently.

        For multiple portfolios, uses a single database query for efficiency.
        For a single portfolio, uses load_portfolio() for caching benefits.

        Args:
            portfolio_names: List of portfolio names to load

        Returns:
            List of Portfolio objects (in order of portfolio_names)
        """
        if not portfolio_names:
            return []

        if len(portfolio_names) == 1:
            portfolio = self.load_portfolio(portfolio_names[0])
            return [portfolio] if portfolio else []

        # Check cache for all portfolios
        cached = []
        to_load = []
        for name in portfolio_names:
            if name in self._cache:
                cached.append(name)
            else:
                to_load.append(name)

        if cached:
            logger.debug(f"Cache hit for {len(cached)} portfolios: {cached}")

        # Load any missing portfolios with multi-query
        portfolios_dict = {}

        if to_load:
            logger.debug(f"Loading {len(to_load)} portfolios from database: {to_load}")
            loaded = self.portfolio_manager.reconstruct_portfolios_from_database(to_load)

            for portfolio in loaded:
                portfolios_dict[portfolio.name] = portfolio
                self._cache[portfolio.name] = portfolio

        # Add cached portfolios
        for name in cached:
            portfolios_dict[name] = self._cache[name]

        # Return in requested order
        result = []
        for name in portfolio_names:
            if name in portfolios_dict:
                result.append(portfolios_dict[name])
            else:
                logger.warning(f"Portfolio not found: {name}")

        logger.info(f"Loaded {len(result)} portfolios from database")
        return result

    def ensure_loaded(self, portfolio_names: Optional[List[str]] = None) -> List[Portfolio]:
        """Ensure requested portfolios are loaded, using session cache if available.

        This is the primary method to use for loading portfolios in UI components.
        It handles both session state and database caching intelligently.

        Args:
            portfolio_names: List of portfolio names to load. If None, loads
                           currently selected portfolios from session state.

        Returns:
            List of loaded Portfolio objects
        """
        if portfolio_names is None:
            portfolio_names = SessionManager.get_selected_portfolios()

        if not portfolio_names:
            logger.warning("No portfolios requested or selected")
            return []

        return self.load_portfolios(portfolio_names)

    def clear_cache(self):
        """Clear the portfolio cache.

        Use this when portfolios are modified (deleted, added, updated) in database.
        """
        logger.info(f"Clearing portfolio cache ({len(self._cache)} items)")
        self._cache.clear()

    def invalidate(self, portfolio_name: str):
        """Invalidate cache for a specific portfolio.

        Use this when a specific portfolio is modified.

        Args:
            portfolio_name: Name of portfolio to invalidate
        """
        if portfolio_name in self._cache:
            logger.debug(f"Invalidating cache for portfolio: {portfolio_name}")
            del self._cache[portfolio_name]
