"""
Data Analyzer Module

Statistical analysis engine for research data.
"""

from pathlib import Path
from typing import Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd
import numpy as np
from scipy import stats
from scipy.stats import shapiro, pearsonr, spearmanr, kruskal, f_oneway, ttest_ind, mannwhitneyu

try:
    import xarray as xr
    HAS_XARRAY = True
except ImportError:
    HAS_XARRAY = False


@dataclass
class DescriptiveStats:
    """Descriptive statistics result"""
    mean: float
    median: float
    std: float
    min: float
    max: float
    q25: float
    q75: float
    skewness: float
    kurtosis: float
    count: int


@dataclass
class DistributionAnalysis:
    """Distribution analysis result"""
    histogram_data: list[int]
    bin_edges: list[float]
    normality_test: dict
    skewness: float
    kurtosis: float


@dataclass
class CorrelationResult:
    """Correlation analysis result"""
    correlation_matrix: pd.DataFrame
    method: str
    significant_pairs: list[dict]


@dataclass
class GroupComparisonResult:
    """Group comparison result"""
    groups: list[str]
    test_name: str
    statistic: float
    p_value: float
    is_significant: bool
    effect_size: float
    post_hoc_results: Optional[list[dict]] = None


class DataAnalyzer:
    """Data analysis engine for research data"""

    def __init__(self):
        pass

    def descriptive_stats(self, df: pd.DataFrame, columns: Optional[list[str]] = None) -> dict[str, DescriptiveStats]:
        """
        Calculate descriptive statistics.

        Args:
            df: Input DataFrame
            columns: Optional list of columns to analyze

        Returns:
            Dictionary mapping column names to DescriptiveStats
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        results = {}
        for col in columns:
            if col not in df.columns:
                continue

            data = df[col].dropna()

            if len(data) == 0:
                continue

            results[col] = DescriptiveStats(
                mean=float(data.mean()),
                median=float(data.median()),
                std=float(data.std()),
                min=float(data.min()),
                max=float(data.max()),
                q25=float(data.quantile(0.25)),
                q75=float(data.quantile(0.75)),
                skewness=float(stats.skew(data)),
                kurtosis=float(stats.kurtosis(data)),
                count=len(data),
            )

        return results

    def distribution_analysis(self, df: pd.DataFrame, column: str) -> DistributionAnalysis:
        """
        Analyze distribution of a column.

        Args:
            df: Input DataFrame
            column: Column name to analyze

        Returns:
            DistributionAnalysis with histogram, normality test, etc.
        """
        data = df[column].dropna()

        hist, bin_edges = np.histogram(data, bins='auto')
        bin_edges = bin_edges.tolist()
        hist = hist.tolist()

        if len(data) >= 3 and len(data) <= 5000:
            stat, p_value = shapiro(data)
            is_normal = p_value > 0.05
            test_name = "Shapiro-Wilk"
        else:
            stat, p_value = stats.normaltest(data)
            is_normal = p_value > 0.05
            test_name = "D'Agostino-Pearson"

        skew = float(stats.skew(data))
        kurt = float(stats.kurtosis(data))

        return DistributionAnalysis(
            histogram_data=hist,
            bin_edges=bin_edges,
            normality_test={
                "statistic": float(stat),
                "p_value": float(p_value),
                "is_normal": is_normal,
                "test_name": test_name
            },
            skewness=skew,
            kurtosis=kurt,
        )

    def correlation_analysis(
        self,
        df: pd.DataFrame,
        columns: Optional[list[str]] = None,
        method: str = "pearson"
    ) -> CorrelationResult:
        """
        Calculate correlation matrix.

        Args:
            df: Input DataFrame
            columns: Optional list of columns to correlate
            method: 'pearson', 'spearman', or 'kendall'

        Returns:
            CorrelationResult with matrix and significant pairs
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        corr_matrix = df[columns].corr(method=method)

        significant_pairs = []
        for i, col1 in enumerate(columns):
            for j, col2 in enumerate(columns):
                if i < j:
                    data1 = df[col1].dropna()
                    data2 = df[col2].dropna()
                    common_idx = data1.index.intersection(data2.index)

                    if len(common_idx) > 2:
                        if method == "spearman":
                            r, p = spearmanr(df.loc[common_idx, col1], df.loc[common_idx, col2])
                        else:
                            r, p = pearsonr(df.loc[common_idx, col1], df.loc[common_idx, col2])

                        if p < 0.05:
                            significant_pairs.append({
                                "var1": col1,
                                "var2": col2,
                                "correlation": float(r),
                                "p_value": float(p),
                                "n": len(common_idx)
                            })

        return CorrelationResult(
            correlation_matrix=corr_matrix,
            method=method,
            significant_pairs=sorted(significant_pairs, key=lambda x: abs(x["correlation"]), reverse=True)
        )

    def group_comparison(
        self,
        df: pd.DataFrame,
        group_col: str,
        value_col: str,
        test: str = "auto"
    ) -> GroupComparisonResult:
        """
        Compare groups using statistical tests.

        Args:
            df: Input DataFrame
            group_col: Column defining groups
            value_col: Column with values to compare
            test: 'anova', 'kruskal', 'ttest', 'mann', or 'auto'

        Returns:
            GroupComparisonResult
        """
        groups = df[group_col].unique()
        group_data = [df[df[group_col] == g][value_col].dropna() for g in groups]

        valid_groups = [g for g, d in zip(groups, group_data) if len(d) >= 2]
        valid_data = [d for d in group_data if len(d) >= 2]

        if len(valid_groups) < 2:
            return GroupComparisonResult(
                groups=list(groups),
                test_name="none",
                statistic=0.0,
                p_value=1.0,
                is_significant=False,
                effect_size=0.0,
            )

        if test == "auto":
            all_normal = all(
                len(d) >= 3 and shapiro(d)[1] > 0.05
                for d in valid_data
            )
            test = "anova" if all_normal else "kruskal"

        if test == "anova":
            stat, p = f_oneway(*valid_data)
            effect = self._eta_squared(df, group_col, value_col)
            test_name = "One-way ANOVA"
        elif test == "kruskal":
            stat, p = kruskal(*valid_data)
            effect = self._epsilon_squared(df, group_col, value_col)
            test_name = "Kruskal-Wallis"
        elif test == "ttest" and len(valid_groups) == 2:
            stat, p = ttest_ind(*valid_data)
            effect = self._cohens_d(*valid_data)
            test_name = "Independent t-test"
        elif test == "mann" and len(valid_groups) == 2:
            stat, p = mannwhitneyu(*valid_data)
            effect = self._rank_biserial(*valid_data)
            test_name = "Mann-Whitney U"
        else:
            stat, p = kruskal(*valid_data)
            effect = 0.0
            test_name = "Kruskal-Wallis (fallback)"

        post_hoc = None
        if p < 0.05 and len(valid_groups) > 2:
            post_hoc = self._post_hoc_tests(df, group_col, value_col, test)

        return GroupComparisonResult(
            groups=list(valid_groups),
            test_name=test_name,
            statistic=float(stat),
            p_value=float(p),
            is_significant=p < 0.05,
            effect_size=float(effect),
            post_hoc_results=post_hoc,
        )

    def _eta_squared(self, df: pd.DataFrame, group_col: str, value_col: str) -> float:
        """Calculate eta-squared effect size for ANOVA"""
        groups = df.groupby(group_col)[value_col]
        ss_between = sum(len(g) * (g.mean() - df[value_col].mean()) ** 2 for _, g in groups)
        ss_total = sum((df[value_col] - df[value_col].mean()) ** 2)
        return ss_between / ss_total if ss_total > 0 else 0

    def _epsilon_squared(self, df: pd.DataFrame, group_col: str, value_col: str) -> float:
        """Calculate epsilon-squared effect size for Kruskal-Wallis"""
        n = len(df)
        groups = df.groupby(group_col)[value_col]
        ranks = df[value_col].rank()
        H = sum(len(g) * (ranks[df[group_col] == g].mean() - ranks.mean()) ** 2 for g, (_, g) in enumerate(groups)) * 12 / (n * (n + 1))
        return (H - len(groups) + 1) / (n - len(groups)) if n > len(groups) else 0

    def _cohens_d(self, group1: pd.Series, group2: pd.Series) -> float:
        """Calculate Cohen's d effect size"""
        n1, n2 = len(group1), len(group2)
        var1, var2 = group1.var(), group2.var()
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        return (group1.mean() - group2.mean()) / pooled_std if pooled_std > 0 else 0

    def _rank_biserial(self, group1: pd.Series, group2: pd.Series) -> float:
        """Calculate rank-biserial correlation for Mann-Whitney"""
        n1, n2 = len(group1), len(group2)
        U, _ = mannwhitneyu(group1, group2)
        return 1 - 2 * U / (n1 * n2)

    def _post_hoc_tests(self, df: pd.DataFrame, group_col: str, value_col: str, base_test: str) -> list[dict]:
        """Perform post-hoc pairwise comparisons"""
        from itertools import combinations

        groups = df[group_col].unique()
        results = []

        for g1, g2 in combinations(groups, 2):
            data1 = df[df[group_col] == g1][value_col].dropna()
            data2 = df[df[group_col] == g2][value_col].dropna()

            if len(data1) < 2 or len(data2) < 2:
                continue

            if base_test == "anova":
                stat, p = ttest_ind(data1, data2)
                test_name = "t-test"
            else:
                stat, p = mannwhitneyu(data1, data2)
                test_name = "Mann-Whitney"

            n_comparisons = len(list(combinations(groups, 2)))
            p_corrected = min(p * n_comparisons, 1.0)

            results.append({
                "group1": str(g1),
                "group2": str(g2),
                "test": test_name,
                "statistic": float(stat),
                "p_value": float(p),
                "p_corrected": float(p_corrected),
                "significant": p_corrected < 0.05,
            })

        return results

    def time_series_analysis(
        self,
        df: pd.DataFrame,
        time_col: str,
        value_col: str,
        freq: Optional[str] = None
    ) -> dict:
        """
        Analyze time series data.

        Args:
            df: Input DataFrame
            time_col: Column with datetime values
            value_col: Column with values
            freq: Optional frequency string ('D', 'M', 'Y', etc.)

        Returns:
            Dictionary with trend and seasonality info
        """
        df_ts = df.copy()
        df_ts[time_col] = pd.to_datetime(df_ts[time_col])
        df_ts = df_ts.sort_values(time_col)

        values = df_ts[value_col].values

        x = np.arange(len(values))
        slope, intercept, r_value, p_value, std_err = stats.linregress(x, values)

        ma_window = min(7, len(values) // 4) if len(values) > 7 else len(values)
        ma = pd.Series(values).rolling(window=ma_window, center=True).mean().tolist()

        return {
            "trend": {
                "slope": float(slope),
                "intercept": float(intercept),
                "r_squared": float(r_value ** 2),
                "p_value": float(p_value),
                "direction": "increasing" if slope > 0 else "decreasing",
            },
            "moving_average": ma,
            "values": values.tolist(),
            "timestamps": df_ts[time_col].tolist(),
            "summary": {
                "count": len(values),
                "mean": float(np.mean(values)),
                "std": float(np.std(values)),
                "min": float(np.min(values)),
                "max": float(np.max(values)),
            }
        }

    def detect_anomalies(
        self,
        df: pd.DataFrame,
        columns: Optional[list[str]] = None,
        method: str = "iqr"
    ) -> pd.DataFrame:
        """
        Detect anomalies in data.

        Args:
            df: Input DataFrame
            columns: Columns to check
            method: 'iqr', 'zscore', or 'isolation_forest'

        Returns:
            DataFrame with anomaly flags
        """
        if columns is None:
            columns = df.select_dtypes(include=[np.number]).columns.tolist()

        result = df.copy()
        result["is_anomaly"] = False
        result["anomaly_score"] = 0.0

        for col in columns:
            if col not in df.columns:
                continue

            data = df[col].dropna()

            if method == "iqr":
                Q1, Q3 = data.quantile([0.25, 0.75])
                IQR = Q3 - Q1
                lower, upper = Q1 - 1.5 * IQR, Q3 + 1.5 * IQR
                anomaly_mask = (df[col] < lower) | (df[col] > upper)
                scores = np.abs((df[col] - data.mean()) / data.std())

            elif method == "zscore":
                scores = np.abs((df[col] - data.mean()) / data.std())
                anomaly_mask = scores > 3

            else:
                try:
                    from sklearn.ensemble import IsolationForest
                    X = df[[col]].fillna(data.mean())
                    iso = IsolationForest(contamination=0.1, random_state=42)
                    anomaly_mask = iso.fit_predict(X) == -1
                    scores = -iso.score_samples(X)
                except ImportError:
                    scores = np.zeros(len(df))
                    anomaly_mask = np.zeros(len(df), dtype=bool)

            result.loc[anomaly_mask, "is_anomaly"] = True
            result.loc[anomaly_mask, "anomaly_score"] = scores[anomaly_mask]

        return result

    def generate_summary_report(self, df: pd.DataFrame) -> str:
        """Generate a text summary report of the data."""
        lines = []
        lines.append("=" * 60)
        lines.append("DATA SUMMARY REPORT")
        lines.append("=" * 60)
        lines.append(f"\nShape: {df.shape[0]} rows x {df.shape[1]} columns")
        lines.append(f"Missing values: {df.isnull().sum().sum()} ({df.isnull().sum().sum() / df.size * 100:.1f}%)")

        numeric_cols = df.select_dtypes(include=[np.number]).columns
        if len(numeric_cols) > 0:
            lines.append(f"\nNumeric columns ({len(numeric_cols)}):")
            for col in numeric_cols[:10]:
                stats_result = self.descriptive_stats(df, [col])[col]
                lines.append(f"  - {col}: mean={stats_result.mean:.3f}, std={stats_result.std:.3f}, range=[{stats_result.min:.3f}, {stats_result.max:.3f}]")

        cat_cols = df.select_dtypes(include=['object', 'category']).columns
        if len(cat_cols) > 0:
            lines.append(f"\nCategorical columns ({len(cat_cols)}):")
            for col in cat_cols[:5]:
                n_unique = df[col].nunique()
                lines.append(f"  - {col}: {n_unique} unique values")

        lines.append("\n" + "=" * 60)
        return "\n".join(lines)


class RemoteSensingAnalyzer:
    """Extended analyzer for remote sensing data"""

    def __init__(self):
        self.data_analyzer = DataAnalyzer()

    def calculate_classification_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        class_names: Optional[list[str]] = None
    ) -> dict:
        """
        Calculate classification metrics for remote sensing.

        Args:
            y_true: Ground truth labels
            y_pred: Predicted labels
            class_names: Optional list of class names

        Returns:
            Dictionary with metrics
        """
        from sklearn.metrics import (
            accuracy_score, cohen_kappa_score, f1_score,
            precision_score, recall_score, confusion_matrix
        )

        classes = np.unique(np.concatenate([y_true, y_pred]))
        n_classes = len(classes)

        if class_names is None:
            class_names = [f"Class_{i}" for i in classes]

        oa = accuracy_score(y_true, y_pred)
        kappa = cohen_kappa_score(y_true, y_pred)

        per_class_metrics = []
        cm = confusion_matrix(y_true, y_pred, labels=classes)

        for i, cls in enumerate(classes):
            if cm.shape[0] > i and cm.shape[1] > i:
                tp = cm[i, i]
                fp = cm[:, i].sum() - tp
                fn = cm[i, :].sum() - tp
                support = cm[i, :].sum()

                precision = tp / (tp + fp) if (tp + fp) > 0 else 0
                recall = tp / (tp + fn) if (tp + fn) > 0 else 0
                f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
                iou = tp / (tp + fp + fn) if (tp + fp + fn) > 0 else 0

                per_class_metrics.append({
                    "class_id": int(cls),
                    "class_name": class_names[i] if i < len(class_names) else f"Class_{cls}",
                    "precision": float(precision),
                    "recall": float(recall),
                    "f1_score": float(f1),
                    "iou": float(iou),
                    "support": int(support),
                })

        macro_f1 = f1_score(y_true, y_pred, average='macro', zero_division=0)
        weighted_f1 = f1_score(y_true, y_pred, average='weighted', zero_division=0)
        macro_precision = precision_score(y_true, y_pred, average='macro', zero_division=0)
        weighted_precision = precision_score(y_true, y_pred, average='weighted', zero_division=0)
        macro_recall = recall_score(y_true, y_pred, average='macro', zero_division=0)
        weighted_recall = recall_score(y_true, y_pred, average='weighted', zero_division=0)

        return {
            "overall_accuracy": float(oa),
            "kappa": float(kappa),
            "macro_f1": float(macro_f1),
            "weighted_f1": float(weighted_f1),
            "macro_precision": float(macro_precision),
            "weighted_precision": float(weighted_precision),
            "macro_recall": float(macro_recall),
            "weighted_recall": float(weighted_recall),
            "per_class": per_class_metrics,
            "confusion_matrix": cm.tolist(),
            "confusion_matrix_labels": class_names[:len(cm)],
        }

    def calculate_regression_metrics(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray
    ) -> dict:
        """
        Calculate regression metrics.

        Args:
            y_true: Ground truth values
            y_pred: Predicted values

        Returns:
            Dictionary with metrics
        """
        from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

        mse = mean_squared_error(y_true, y_pred)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_true, y_pred)
        r2 = r2_score(y_true, y_pred)

        mask = y_true != 0
        if mask.sum() > 0:
            mape = np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100
        else:
            mape = np.nan

        return {
            "mse": float(mse),
            "rmse": float(rmse),
            "mae": float(mae),
            "r2": float(r2),
            "mape": float(mape) if not np.isnan(mape) else None,
        }

    def generate_confusion_matrix(
        self,
        y_true: np.ndarray,
        y_pred: np.ndarray,
        class_names: Optional[list[str]] = None
    ) -> dict:
        """Generate confusion matrix data for visualization."""
        from sklearn.metrics import confusion_matrix

        classes = np.unique(np.concatenate([y_true, y_pred]))
        if class_names is None:
            class_names = [f"Class_{i}" for i in classes]

        cm = confusion_matrix(y_true, y_pred, labels=classes)
        cm_normalized = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        cm_normalized = np.nan_to_num(cm_normalized)

        return {
            "matrix": cm.tolist(),
            "normalized": cm_normalized.tolist(),
            "labels": class_names[:len(cm)],
            "n_classes": len(classes),
        }

    def spatial_autocorrelation(
        self,
        data: np.ndarray,
        coords: Optional[tuple[np.ndarray, np.ndarray]] = None
    ) -> dict:
        """
        Calculate spatial autocorrelation (Moran's I).

        Args:
            data: 2D array of values
            coords: Optional (x, y) coordinate arrays

        Returns:
            Dictionary with Moran's I and statistics
        """
        flat_data = data.flatten()

        if coords is not None:
            x, y = coords
            flat_x, flat_y = x.flatten(), y.flatten()
        else:
            rows, cols = data.shape
            flat_x = np.repeat(np.arange(cols), rows)
            flat_y = np.tile(np.arange(rows), cols)

        from scipy.spatial.distance import cdist
        coords_flat = np.column_stack([flat_x, flat_y])
        distances = cdist(coords_flat, coords_flat)

        distances[distances == 0] = 1
        weights = 1 / distances
        weights = weights / weights.sum(axis=1, keepdims=True)

        n = len(flat_data)
        mean_val = np.mean(flat_data)
        centered = flat_data - mean_val

        z = centered / np.std(flat_data) if np.std(flat_data) > 0 else centered
        numerator = np.sum(weights * np.outer(z, z))
        denominator = np.sum(z ** 2) / n
        morans_i = numerator / denominator

        z_score = morans_i / 0.089
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

        return {
            "morans_i": float(morans_i),
            "z_score": float(z_score),
            "p_value": float(p_value),
            "interpretation": self._interpret_morans_i(morans_i),
            "n_points": n,
        }

    def _interpret_morans_i(self, i: float) -> str:
        """Interpret Moran's I value."""
        if i > 0.1:
            return "Strong positive spatial autocorrelation (clustered)"
        elif i > 0:
            return "Moderate positive spatial autocorrelation"
        elif i < -0.1:
            return "Strong negative spatial autocorrelation (dispersed)"
        elif i < 0:
            return "Moderate negative spatial autocorrelation"
        else:
            return "No significant spatial autocorrelation (random)"

    def change_detection(
        self,
        raster1: np.ndarray,
        raster2: np.ndarray,
        method: str = "difference"
    ) -> np.ndarray:
        """
        Detect changes between two rasters.

        Args:
            raster1: First raster array
            raster2: Second raster array
            method: 'difference', 'ratio', or 'binary'

        Returns:
            Change detection result array
        """
        if method == "difference":
            return raster2 - raster1
        elif method == "ratio":
            with np.errstate(divide='ignore', invalid='ignore'):
                ratio = raster2 / raster1
                ratio[~np.isfinite(ratio)] = 0
                return ratio
        elif method == "binary":
            threshold = np.std(raster2 - raster1) * 2
            return np.abs(raster2 - raster1) > threshold
        else:
            raise ValueError(f"Unknown method: {method}")
