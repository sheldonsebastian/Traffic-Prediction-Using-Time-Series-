import warnings

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

from ToolBox import split_df_train_test, plot_line_using_pandas_index, cal_auto_correlation, plot_acf, plot_heatmap, \
    create_gpac_table, gpac_order_chi_square_test, statsmodels_estimate_parameters, statsmodels_print_parameters, \
    statsmodels_print_confidence_interval, statsmodels_print_roots_AR, statsmodels_print_roots_MA, \
    plot_multiline_chart_pandas_using_index, normal_equation_using_statsmodels, \
    normal_equation_prediction_using_statsmodels, cal_mse, cal_forecast_errors, box_pierce_test, adf_cal, \
    plot_seasonal_decomposition, generic_holt_linear_winter, statsmodels_predict_ARMA_process, \
    statsmodels_print_covariance_matrix, statsmodels_print_variance_error, gpac_order_chi_square_test2, \
    generic_average_method

if __name__ == "__main__":
    # pandas print options
    pd.set_option("max_columns", 10)

    # ignore warnings
    warnings.filterwarnings("ignore")

    # read the original data
    traffic_raw = pd.read_csv("./data/Metro_Interstate_Traffic_Volume.csv")

    # replace all the None values with nan
    traffic_copy = traffic_raw.replace("None", np.nan)

    # convert date string column to date time object
    traffic_copy["date_time"] = pd.to_datetime(traffic_copy["date_time"], format="%Y-%m-%d")
    traffic_copy = traffic_copy.set_index(traffic_copy["date_time"])

    # focus on data from 09/2016 to 09/2018
    traffic_clipped = traffic_copy.loc['2016-09-30':'2018-09-30'].copy(deep=True)

    # resample based on daily data
    traffic_resampled = traffic_clipped.groupby(pd.Grouper(freq="D")).aggregate(
        {"temp": "mean", "clouds_all": "mean", "weather_main": "first", "traffic_volume": "mean", "holiday": "first",
         "rain_1h": "mean", "snow_1h": "mean"})

    print()
    print("The dimension of the resampled data is as follows:")
    print(traffic_resampled.shape)

    print()
    print("The summary statistics of numeric data after resampling to daily data is:")
    print(traffic_resampled.describe(include=["float64"]))

    # drop the snow_1h column
    traffic_resampled.drop(["snow_1h"], axis=1, inplace=True)

    print()
    print("The summary statistics of categorical data after resampling to daily data is:")
    print(traffic_resampled.describe(include=["object"]))

    traffic_resampled["holiday"] = traffic_resampled["holiday"].replace({np.nan: "No Holiday"})
    print()
    print("After replacing all the holiday NaN columns with 'No Holiday' value we get value counts for holiday column "
          "as:")
    print(traffic_resampled["holiday"].value_counts())

    # weather_main column value counts before condensing
    print()
    print("The value counts for weather_main column before condensing it:")
    print(traffic_resampled["weather_main"].value_counts())

    # condense the weather main categorical values
    traffic_resampled = traffic_resampled.replace(
        {"weather_main": {"Drizzle": "Rain", "Thunderstorm": "Rain", "Mist": "Fog", "Haze": "Fog", "Smoke": "Fog"}})

    # weather_main column value counts after condensing
    print()
    print("The value counts for weather_main column after condensing it:")
    print(traffic_resampled["weather_main"].value_counts())

    # after resampling we find these many NaN rows
    print()
    print("After resampling and data cleaning, column count with NaN values are:")
    print(traffic_resampled.isnull().sum())

    # Plot of the dependent variable versus time.
    plot_line_using_pandas_index(traffic_resampled, "traffic_volume", "Traffic Volume over time", "Navy", "Time",
                                 y_axis_label="Traffic Volume")

    # ACF of the dependent variable.
    autocorrelation = cal_auto_correlation(list(traffic_resampled["traffic_volume"]), 200)
    plot_acf(autocorrelation, "ACF plot for Traffic Volume")

    # Correlation Matrix with seaborn heatmap and pearson’s correlation coefficient
    corr = traffic_resampled.corr()
    plot_heatmap(corr, "Heatmap for Correlation Coefficient for Traffic Volume Data")

    # split into train and test(20%) dataset
    train, test = split_df_train_test(traffic_resampled, 0.2)

    # to keep track of performance for all the models
    result_performance = pd.DataFrame(
        {"Model": [], "MSE": [], "RMSE": [], "Residual Mean": [], "Residual Variance": []})

    # average model
    average_predictions = generic_average_method(train["traffic_volume"], len(test["traffic_volume"]))

    # plot the predicted vs actual data
    average_df = test.copy(deep=True)
    average_df["traffic_volume"] = average_predictions

    plot_multiline_chart_pandas_using_index([train, test, average_df], "traffic_volume",
                                            ["Train", "Test", "Prediction"], ["Blue", "Orange", "Green"],
                                            "Time", "Traffic Volume",
                                            "Traffic Volume Prediction Using Average",
                                            rotate_xticks=True)

    avg_mse = cal_mse(test["traffic_volume"], average_predictions)
    avg_rmse = np.sqrt(avg_mse)

    residuals_avg = cal_forecast_errors(test["traffic_volume"], average_predictions)

    avg_mean = np.mean(residuals_avg)
    avg_variance = np.var(residuals_avg)

    residual_autocorrelation_holt_winter = cal_auto_correlation(residuals_avg, len(average_predictions))
    plot_acf(residual_autocorrelation_holt_winter, "ACF plot using Average Residuals")

    # add the results to common dataframe
    result_performance = result_performance.append(
        pd.DataFrame(
            {"Model": ["Average Model"], "MSE": [avg_mse], "RMSE": [avg_rmse],
             "Residual Mean": [avg_mean], "Residual Variance": [avg_variance]}))

    # dimension of train data
    print()
    print("The dimension of train data is:")
    print(train.shape)

    # dimension of test data
    print()
    print("The dimension of test data is:")
    print(test.shape)

    # combining train and test data
    combined_data = train.append(test)

    # Stationarity
    print()
    adf_cal(combined_data, "traffic_volume")

    # Time series Decomposition
    # the train dataframe already has DateTimeIndex as index which specified the frequency as 'D'
    plot_seasonal_decomposition(train["traffic_volume"], None, "Multiplicative Residuals", "multiplicative")
    plot_seasonal_decomposition(train["traffic_volume"], None, "Additive Residuals", "additive")

    print("--------------------------------------- HOLT WINTER ---------------------------------------")
    # holt winter prediction
    holt_winter_prediction = generic_holt_linear_winter(train["traffic_volume"], test["traffic_volume"], None, None,
                                                        "mul", None)
    # holt winter mse
    holt_winter_mse = cal_mse(test["traffic_volume"], holt_winter_prediction)

    print()
    print("The MSE for Holt Winter model is:")
    print(holt_winter_mse)

    # holt winter rmse
    holt_winter_rmse = np.sqrt(holt_winter_mse)
    print()
    print("The RMSE for Holt Winter model is:")
    print(holt_winter_rmse)

    # holt winter residual
    residuals_holt_winter = cal_forecast_errors(list(test["traffic_volume"]), holt_winter_prediction)
    residual_autocorrelation_holt_winter = cal_auto_correlation(residuals_holt_winter, len(holt_winter_prediction))

    # holt winter residual variance
    holt_winter_variance = np.var(residuals_holt_winter)
    print()
    print("The Variance of residual for Holt Winter model is:")
    print(holt_winter_variance)

    # holt winter residual mean
    holt_winter_mean = np.mean(residuals_holt_winter)
    print()
    print("The Mean of residual for Holt Winter model is:")
    print(holt_winter_mean)

    # holt winter residual ACF
    plot_acf(residual_autocorrelation_holt_winter, "ACF plot using Holt Winter Residuals")

    # add the results to common dataframe
    result_performance = result_performance.append(
        pd.DataFrame(
            {"Model": ["Holt Winter Model"], "MSE": [holt_winter_mse], "RMSE": [holt_winter_rmse],
             "Residual Mean": [holt_winter_mean], "Residual Variance": [holt_winter_variance]}))

    # plot the predicted vs actual data
    holt_winter_df = test.copy(deep=True)
    holt_winter_df["traffic_volume"] = holt_winter_prediction

    plot_multiline_chart_pandas_using_index([train, test, holt_winter_df], "traffic_volume",
                                            ["Train", "Test", "Prediction"], ["Blue", "Orange", "Green"],
                                            "Time", "Traffic Volume",
                                            "Traffic Volume Prediction Using Holt Winter",
                                            rotate_xticks=True)

    print("--------------------------------------- MULTIPLE LINEAR REGRESSION-----------------------------")
    lm_combined = combined_data.copy(deep=True)

    # convert categorical into numerical columns
    lm_combined = pd.get_dummies(lm_combined)

    # separate train and test data
    lm_train = lm_combined[:len(train)]
    lm_test = lm_combined[len(train):]

    # Scaling the data using MixMax Scaler
    mm_scaler = MinMaxScaler()
    lm_train_mm_scaled = pd.DataFrame(
        mm_scaler.fit_transform(lm_train[np.setdiff1d(lm_train.columns, ["traffic_volume"])]),
        columns=np.setdiff1d(lm_train.columns, ["traffic_volume"]))
    lm_train_mm_scaled.set_index(lm_train.index, inplace=True)
    lm_train_mm_scaled["traffic_volume"] = lm_train["traffic_volume"]

    lm_test_mm_scaled = pd.DataFrame(mm_scaler.transform(lm_test[np.setdiff1d(lm_test.columns, ["traffic_volume"])]),
                                     columns=np.setdiff1d(lm_test.columns, ["traffic_volume"]))
    lm_test_mm_scaled.set_index(lm_test.index, inplace=True)
    lm_test_mm_scaled["traffic_volume"] = lm_test["traffic_volume"]

    # linear model using all variables
    basic_model = normal_equation_using_statsmodels(
        lm_train_mm_scaled[np.setdiff1d(lm_train_mm_scaled.columns, "traffic_volume")],
        lm_train_mm_scaled["traffic_volume"], intercept=False)

    print()
    print("The summary of linear model with all variables is:")
    print(basic_model.summary())

    features = np.setdiff1d(lm_train_mm_scaled.columns,
                            ["rain_1h", "holiday_Christmas Day", "holiday_Memorial Day", "holiday_Thanksgiving Day",
                             "holiday_New Years Day", "holiday_Independence Day", "holiday_Labor Day", "clouds_all",
                             "holiday_Washingtons Birthday", "holiday_Martin Luther King Jr Day"])

    # linear model using features which pass the t-test
    pruned_model = normal_equation_using_statsmodels(lm_train_mm_scaled[np.setdiff1d(features, "traffic_volume")],
                                                     lm_train_mm_scaled["traffic_volume"], intercept=False)

    print()
    print("The summary of linear model after feature selection:")
    print(pruned_model.summary())

    # linear model predictions
    lm_predictions = normal_equation_prediction_using_statsmodels(pruned_model, lm_test_mm_scaled[
        np.setdiff1d(features, "traffic_volume")], intercept=False)

    # linear model mse
    lm_mse = cal_mse(test["traffic_volume"], lm_predictions)

    print()
    print("The MSE for Linear Model model is:")
    print(lm_mse)

    # linear model rmse
    lm_rmse = np.sqrt(lm_mse)
    print()
    print("The RMSE for Linear Model model is:")
    print(lm_rmse)

    # linear model residual
    residuals_lm = cal_forecast_errors(list(test["traffic_volume"]), lm_predictions)
    residual_autocorrelation = cal_auto_correlation(residuals_lm, len(lm_predictions))

    # linear model residual variance
    lm_variance = np.var(residuals_lm)
    print()
    print("The Variance of residual for Linear Model model is:")
    print(lm_variance)

    # linear model residual mean
    lm_mean = np.mean(residuals_lm)
    print()
    print("The Mean of residual for Linear Model model is:")
    print(lm_mean)

    # linear model residual ACF
    plot_acf(residual_autocorrelation, "ACF plot for Linear Model Residuals")

    # linear model Q value
    Q_value_lm = box_pierce_test(len(test), residuals_lm, len(test))
    print()
    print("The Q Value of residuals for Linear Model model is:")
    print(Q_value_lm)

    # add the results to common dataframe
    result_performance = result_performance.append(
        pd.DataFrame(
            {"Model": ["Multiple Linear Regression Model"], "MSE": [lm_mse], "RMSE": [lm_rmse],
             "Residual Mean": [lm_mean], "Residual Variance": [lm_variance]}))

    # plot the actual vs predicted values
    lm_predictions_scaled = lm_test_mm_scaled.copy(deep=True)
    lm_predictions_scaled["traffic_volume"] = lm_predictions

    plot_multiline_chart_pandas_using_index([lm_train_mm_scaled, lm_test_mm_scaled, lm_predictions_scaled],
                                            "traffic_volume",
                                            ["Train", "Test", "Prediction"], ["Blue", "Orange", "Green"],
                                            "Time", "Traffic Volume",
                                            "Traffic Volume Prediction Using Multiple Linear Model",
                                            rotate_xticks=True)

    # correlation coefficient for linear model after feature selection
    corr = lm_train[features].corr()
    label_ticks = ["Columbus Day", "No Holiday", "State Fair", "Veterans Day", "temp", "traffic_volume", "Clear",
                   "Clouds", "Fog", "Rain", "Snow"]
    plot_heatmap(corr, "Correlation Coefficient for Linear Model after feature selection", label_ticks, label_ticks, 45)

    print("--------------------------------------- ARMA ---------------------------------------")
    j = 12
    k = 12
    lags = j + k
    y = train["traffic_volume"]

    # autocorrelation of traffic volume
    ry = cal_auto_correlation(y, lags)

    # create GPAC Table
    gpac_table = create_gpac_table(j, k, ry)
    print()
    print("GPAC Table:")
    print(gpac_table.to_string())
    print()

    plot_heatmap(gpac_table, "GPAC Table for Traffic Volume")

    # estimate the order of the process
    # possible_order = [(2, 0), (2, 5), (2, 7), (4, 0), (4, 2), (4, 5), (4, 7), (4, 10), (6, 5), (7, 0), (7, 8), (10, 3)]
    possible_order = []
    print()
    print("The possible orders for ARMA process are:")
    print(possible_order)
    print()

    # checking which orders pass the GPAC test
    pass_order = gpac_order_chi_square_test(possible_order, y, "2018-05-07 00:00:00", "2018-09-30 00:00:00", lags,
                                            test["traffic_volume"])

    print()
    print("The orders of ARMA process which pass the chi square test are:")
    print(pass_order)

    # creating an ARMA(6,5) model
    n_a = 6
    n_b = 5
    model = statsmodels_estimate_parameters(n_a, n_b, y)

    # print the estimated paramters
    print()
    print(f"The estimated parameters for ARMA({n_a}, {n_b}) are:")
    statsmodels_print_parameters(model, n_a, n_b)

    # print the confidence interval for the estimated parameters
    statsmodels_print_confidence_interval(model, n_a, n_b)

    # AR roots (denominator)
    print("The roots of denominator(AR) are:")
    statsmodels_print_roots_AR(model)

    # MA roots (numerator)
    print()
    print("The roots of numerator(MA) are:")
    statsmodels_print_roots_MA(model)
    print()

    # ARMA predictions
    arma_prediction = statsmodels_predict_ARMA_process(model, "2018-05-07 00:00:00", "2018-09-30 00:00:00")

    # ARMA mse
    arma_mse = cal_mse(test["traffic_volume"], arma_prediction)

    print("The MSE for ARMA model is:")
    print(arma_mse)

    # ARMA rmse
    arma_rmse = np.sqrt(arma_mse)
    print()
    print("The RMSE for ARMA model is:")
    print(arma_rmse)

    # ARMA residual
    residuals_arma = cal_forecast_errors(list(test["traffic_volume"]), arma_prediction)

    # ARMA residual variance
    arma_variance = np.var(residuals_arma)
    print()
    print("The Variance of residual for ARMA model is:")
    print(arma_variance)

    # ARMA residual mean
    arma_mean = np.mean(residuals_arma)
    print()
    print("The Mean of residual for ARMA model is:")
    print(arma_mean)

    # ARMA residual ACF
    residual_autocorrelation_arma = cal_auto_correlation(residuals_arma, len(arma_prediction))
    plot_acf(residual_autocorrelation_arma, "ACF plot using ARMA Residuals")

    # ARMA covariance matrix
    print()
    statsmodels_print_covariance_matrix(model, n_a, n_b)

    # ARMA estimated variance of error
    statsmodels_print_variance_error(model, n_a, n_b)

    # add the results to common dataframe
    result_performance = result_performance.append(
        pd.DataFrame(
            {"Model": ["ARMA Model"], "MSE": [arma_mse], "RMSE": [arma_rmse],
             "Residual Mean": [arma_mean], "Residual Variance": [arma_variance]}))

    # plot the predicted vs actual data
    arma_df = test.copy(deep=True)
    arma_df["traffic_volume"] = arma_prediction

    plot_multiline_chart_pandas_using_index([train, test, arma_df], "traffic_volume",
                                            ["Train", "Test", "Prediction"], ["Blue", "Orange", "Green"],
                                            "Time", "Traffic Volume",
                                            "Traffic Volume Prediction Using ARMA",
                                            rotate_xticks=True)

    print()
    print("The performance metrics for all the models is shown:")
    print(result_performance.to_string())

    print("--------------------------------------- ARMA 2 ---------------------------------------")
    n_a = 4
    n_b = 1
    y2 = np.subtract(train["traffic_volume"], np.mean(train["traffic_volume"]))
    model = statsmodels_estimate_parameters(n_a, n_b, y2)

    gpac_order_chi_square_test2([(n_a, n_b)], y2, "2018-05-07 00:00:00", "2018-09-30 00:00:00", lags,
                                test["traffic_volume"], np.mean(train["traffic_volume"]))

    # # print the estimated paramters
    # print()
    # print(f"The estimated parameters for ARMA({n_a}, {n_b}) are:")
    # statsmodels_print_parameters(model, n_a, n_b)
    #
    # # print the confidence interval for the estimated parameters
    # statsmodels_print_confidence_interval(model, n_a, n_b)
    #
    # # AR roots (denominator)
    # print("The roots of denominator(AR) are:")
    # statsmodels_print_roots_AR(model)
    #
    # # MA roots (numerator)
    # print()
    # print("The roots of numerator(MA) are:")
    # statsmodels_print_roots_MA(model)
    # print()
    #
    # # ARMA predictions
    # arma_prediction = statsmodels_predict_ARMA_process(model, "2018-05-07 00:00:00", "2018-09-30 00:00:00")
    #
    # # ARMA mse
    # arma_mse = cal_mse(test["traffic_volume"], np.add(arma_prediction, np.mean(train["traffic_volume"])))
    #
    # print("The MSE for ARMA model is:")
    # print(arma_mse)
    #
    # # ARMA rmse
    # arma_rmse = np.sqrt(arma_mse)
    # print()
    # print("The RMSE for ARMA model is:")
    # print(arma_rmse)
    #
    # # ARMA residual
    # residuals_arma = cal_forecast_errors(list(test["traffic_volume"]), arma_prediction)
    #
    # # ARMA residual variance
    # arma_variance = np.var(residuals_arma)
    # print()
    # print("The Variance of residual for ARMA model is:")
    # print(arma_variance)
    #
    # # ARMA residual mean
    # arma_mean = np.mean(residuals_arma)
    # print()
    # print("The Mean of residual for ARMA model is:")
    # print(arma_mean)
    #
    # # ARMA residual ACF
    # residual_autocorrelation_arma = cal_auto_correlation(residuals_arma, len(arma_prediction))
    # plot_acf(residual_autocorrelation_arma, "ACF plot using ARMA Residuals")
    #
    # # ARMA covariance matrix
    # print()
    # statsmodels_print_covariance_matrix(model, n_a, n_b)
    #
    # # ARMA estimated variance of error
    # statsmodels_print_variance_error(model, n_a, n_b)
    #
    # # add the results to common dataframe
    # result_performance = result_performance.append(
    #     pd.DataFrame(
    #         {"Model": ["ARMA Model"], "MSE": [arma_mse], "RMSE": [arma_rmse],
    #          "Residual Mean": [arma_mean], "Residual Variance": [arma_variance]}))
    #
    # # plot the predicted vs actual data
    # arma_df = test.copy(deep=True)
    # arma_df["traffic_volume"] = arma_prediction
    #
    # plot_multiline_chart_pandas_using_index([train, test, arma_df], "traffic_volume",
    #                                         ["Train", "Test", "Prediction"], ["Blue", "Orange", "Green"],
    #                                         "Time", "Traffic Volume",
    #                                         "Traffic Volume Prediction Using ARMA",
    #                                         rotate_xticks=True)
    #
    # print()
    # print("The performance metrics for all the models is shown:")
    # print(result_performance.to_string())
