from phy_model import fileObject
import pandas as pd
import os
import numpy as np
from sklearn.neighbors import KNeighborsRegressor
from sklearn.multioutput import MultiOutputRegressor
from sklearn.ensemble import RandomForestRegressor
from sklearn.svm import SVR
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error


class ml_fileObject:

    def __init__(self, root, index):
        self.root = root
        self.index = index
        self.path = os.path.join(root, str(index))
        for files in os.listdir(self.path):
            if files.startswith('IMU'):
                self.imu_path = os.path.join(self.path, files)
            elif files.startswith('Mag'):
                self.mag_path = os.path.join(self.path, files)
            elif files.startswith('ultra'):
                self.ultra_path = os.path.join(self.path, files)
        self.height_dict = {
            '1': 0.736,
            '2': 0.782,
            '3': 0.827,
            '4': 0.877,
            '5': 0.936,
            '6': 0.981,
            '7': 1.043,
            '8': 1.102,
            '9': 1.10
        }

    def get_ultra(self):
        Dataframe = pd.read_csv(self.ultra_path, sep=" ",
                                names=["ID", "P_x", "P_y", "P_z", "unknow", "unknow_1", "Time_Stamp"])
        Dataframe = Dataframe.drop(["ID", "unknow", "unknow_1"], axis=1)
        rows, columns = Dataframe.shape
        serial_num = np.arange(0, rows, 1).tolist()
        serial_num_inte = np.arange(0, rows, 0.1).tolist()
        Px_inte = np.interp(serial_num_inte, serial_num, Dataframe["P_x"])
        Py_inte = np.interp(serial_num_inte, serial_num, Dataframe["P_y"])
        Pz_inte = np.interp(serial_num_inte, serial_num, Dataframe["P_z"])
        Pt_inte = np.interp(serial_num_inte, serial_num, Dataframe["Time_Stamp"])
        Dataframe_inte = pd.DataFrame(columns=["Serial_Num", 'P_X', 'P_Y', 'P_Z', "Time_Stamp"])
        Dataframe_inte["Serial_Num"] = np.arange(0, len(serial_num_inte), 1).tolist()
        Dataframe_inte["P_X"] = Px_inte
        Dataframe_inte["P_Y"] = Py_inte
        Dataframe_inte['P_Z'] = self.height_dict[str(self.index)]
        # Dataframe_inte["P_Z"] = Pz_inte
        Dataframe_inte["Time_Stamp"] = Pt_inte
        return Dataframe_inte

    def get_mag(self):
        df_tem = pd.read_csv(self.mag_path, sep=" ", names=["Serial_Num", "R_x", "R_y", "R_z", "Time_Stamp"],
                             index_col="Serial_Num")
        df_tem["Magnitude"] = np.sqrt(
            np.power(df_tem["R_x"], 2) + np.power(df_tem["R_y"], 2) + np.power(df_tem["R_z"], 2))
        return df_tem

    def get_imu(self):
        df_tem = pd.read_csv(self.imu_path, sep=" ",
                             names=['a_x', 'a_y', 'a_z', 'G_x', 'G_y', 'G_z', 'M_x', 'M_y', 'M_z', 'alpha', 'beta',
                                    'gama', 'mill', 'Time_Stamp', 'index'],
                             index_col="index")
        return df_tem

    def get_IMU_info(self, time_mag, df_imu):
        time_imu = df_imu['Time_Stamp'].to_numpy()
        sub_array = abs(time_imu - time_mag)
        index = np.argmin(sub_array)
        alpha, beta, gama = df_imu.iloc[index, 9], df_imu.iloc[index, 10], df_imu.iloc[index, 11]
        a_x, a_y, a_z = df_imu.iloc[index, 0], df_imu.iloc[index, 1], df_imu.iloc[index, 2]
        return a_x, a_y, a_z, alpha, beta, gama

    def get_position(self, time_mag, df_ultra):
        time_ultra = df_ultra['Time_Stamp'].to_numpy()
        sub_array = abs(time_ultra - time_mag)
        index = np.argmin(sub_array)
        p_x, p_y, p_z = df_ultra.iloc[index, 1], df_ultra.iloc[index, 2], df_ultra.iloc[index, 3]
        # print(p_x,p_y,p_z)
        return p_x, p_y, p_z

    def merge_all(self):
        df_mag = self.get_mag()
        df_ultra = self.get_ultra()
        df_imu = self.get_imu()
        position = []
        imu_data = []
        for i in range(df_mag.shape[0]):
            position.append(self.get_position(df_mag.iloc[i, 3], df_ultra))
            imu_data.append(self.get_IMU_info(df_mag.iloc[i, 3], df_imu))
        position_array = np.array(position)
        imu_data_array = np.array(imu_data)
        df_mag['p_x'] = position_array[:, 0]
        df_mag['p_y'] = position_array[:, 1]
        df_mag['p_z'] = position_array[:, 2]
        df_mag['d_t1'] = np.sqrt(
            np.power(position_array[:, 0] - 1.90, 2) + np.power(position_array[:, 1] - 0.17, 2) + np.power(
                position_array[:, 2] - 1.24, 2))
        df_mag['d_t2'] = np.sqrt(
            np.power(position_array[:, 0] - 5.00, 2) + np.power(position_array[:, 1] - 0.33, 2) + np.power(
                position_array[:, 2] - 1.24, 2))
        df_mag['d_t3'] = np.sqrt(
            np.power(position_array[:, 0] - 3.23, 2) + np.power(position_array[:, 1] + 2.94, 2) + np.power(
                position_array[:, 2] - 1.24, 2))
        df_mag['a_x'] = imu_data_array[:, 0]
        df_mag['a_y'] = imu_data_array[:, 1]
        df_mag['a_z'] = imu_data_array[:, 2]
        df_mag['alpha'] = imu_data_array[:, 3]
        df_mag['beta'] = imu_data_array[:, 4]
        df_mag['gama'] = imu_data_array[:, 5]
        return df_mag

    def get_T_index(self, noise_threshould):
        df_mag_merge = self.merge_all()
        mag_array = np.array(df_mag_merge['Magnitude'].tolist())
        mag_index = []
        for rows in range(10, df_mag_merge.shape[0] - 100):
            if np.sum(mag_array[rows - 1:rows + 4]) < np.sum(mag_array[rows:rows + 5]) and np.sum(
                    mag_array[rows + 1:rows + 6]) < np.sum(mag_array[rows:rows + 5]) and np.min(
                mag_array[rows:rows + 5]) > noise_threshould:  #### outdoor: 6800000
                mag_index.append(rows)
        T1_start = []
        T2_start = []
        T3_start = []

        for index in range(len(mag_index) - 3):
            if 7 < mag_index[index + 2] - mag_index[index + 1] < 11 and 7 < mag_index[index + 1] - mag_index[
                index] < 11:
                T1_start.append(mag_index[index])


            elif 10 < mag_index[index + 2] - mag_index[index + 1] < 14 and 7 < mag_index[index + 1] - mag_index[
                index] < 11:
                T2_start.append(mag_index[index])

            elif 7 < mag_index[index + 2] - mag_index[index + 1] < 11 and 10 < mag_index[index + 1] - mag_index[
                index] < 14:
                T3_start.append(mag_index[index])

        return T1_start, T2_start, T3_start

    def get_ml_features(self):
        df_mag_merge = self.merge_all()
        t1,t2,t3 = self.get_T_index(8000000)
        period_start = []
        for item in t1:
            period_start.append(item)
        for item in t2:
            period_start.append(item - 40)
        for item in t3:
            period_start.append(item - 80)
        T1_start = []
        sorted_begin_list = sorted(period_start)
        for i in range(1, len(period_start)):
            if sorted_begin_list[i] - sorted_begin_list[i - 1] > 2:
                T1_start.append(sorted_begin_list[i])
        feature_list = []
        feature_index = []
        for item in T1_start:
            feature_list.append(
                (item, item + 9, item + 18, item + 40, item + 49, item + 60, item + 80, item + 92, item + 102))
            feature_index.extend(
                (item, item + 9, item + 18, item + 40, item + 49, item + 60, item + 80, item + 92, item + 102))
        x_feature = []
        y_feature = []

        for item in feature_list:
            x_feature.append([
                max(df_mag_merge.iloc[item[0]:item[0] + 5, 4]),
                max(df_mag_merge.iloc[item[1]:item[1] + 5, 4]),
                max(df_mag_merge.iloc[item[2]:item[2] + 5, 4]),
                max(df_mag_merge.iloc[item[3]:item[3] + 5, 4]),
                max(df_mag_merge.iloc[item[4]:item[4] + 5, 4]),
                max(df_mag_merge.iloc[item[5]:item[5] + 5, 4]),
                max(df_mag_merge.iloc[item[6]:item[6] + 5, 4]),
                max(df_mag_merge.iloc[item[7]:item[7] + 5, 4]),
                max(df_mag_merge.iloc[item[8]:item[8] + 5, 4]),

            ])
            y_feature.append(
                [df_mag_merge.iloc[item[0], 5], df_mag_merge.iloc[item[0], 6], df_mag_merge.iloc[item[0], 7]])
        return x_feature,y_feature


class ml_model:

    def __init__(self,x_feature,y_feature):

        self.x_feature = x_feature
        self.y_feature = y_feature

    def Random_forest(self,n_estimators=100,max_depth=15):
        rf_reg = MultiOutputRegressor(RandomForestRegressor(n_estimators=n_estimators,max_depth=max_depth,random_state=0))
        rf_reg.fit(self.x_feature, self.y_feature)
        return rf_reg

    def KNeighbors(self,neighors):
        rf_knn = MultiOutputRegressor(KNeighborsRegressor(neighors=neighors))
        rf_knn.fit(self.x_feature,self.y_feature)
        return rf_knn

    def Svm(self,kernel='rbf',gamma=0.1,epsilon=0.1):
        rf_svm = MultiOutputRegressor(SVR(kernel=kernel,gamma=gamma,epsilon=epsilon))
        rf_svm.fit(self.x_feature,self.y_feature)
        return rf_svm




if __name__ == '__main__':
    root = '/Users/guoqiushi/Documents/thesis/indoor_final/'
    file_1  = ml_fileObject(root,1)
    x_feature,y_feature = file_1.get_ml_features()
    svm_model = ml_model(x_feature,y_feature)
    print(svm_model.Svm())

