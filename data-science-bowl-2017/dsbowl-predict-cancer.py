import glob
import os
import csv
import re
import pandas as pd
import numpy as np
import SimpleITK as sitk
import matplotlib.pyplot as plt
from tqdm import tqdm
import time
from datetime import timedelta
import sys
import datetime
#import tensorflow as tf
import math
from sklearn import model_selection
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier as RF
import scipy as sp
from sklearn.decomposition import PCA
import sklearn.metrics

def get_patient_labels(patient_ids):
    labels = pd.read_csv(LABELS)
    input_labels = {}
    for patient_id in patient_ids:
        try:
            label = int(labels.loc[labels['id'] == patient_id, 'cancer'])
            input_labels[patient_id] = label
        except TypeError:
            print('ERROR: Couldnt find label for patient {}'.format(patient_id))
            continue
    return input_labels

def get_patient_features(patient_ids):
    input_features = {}
    MAX_CLASS_IDENTIFIER  = 2
    NUM_BINS_1 = 5
    NUM_BINS_0 = 5

    TRESHOLD_1 = 0.00
    TRESHOLD_0 = 0.00


    # import sys
    # orig_stdout = sys.stdout
    # f = open('myfile.txt', 'w')
    # sys.stdout = f

    num_patients = len(patient_ids)
    count = 0
    input_feature_flattened_dims = 0
    for patient_id in patient_ids:
        predictions = np.array(np.load(DATA_PATH + patient_id + '_predictions.npy'))
        transfer_values = np.array(np.load(DATA_PATH + patient_id + '_transfer_values.npy'))

        transfer_values_flatten_shape = (transfer_values.shape[0], transfer_values.shape[4])
        transfer_values_flatten = np.zeros(shape=transfer_values_flatten_shape, dtype=np.float32)
        for i in range(len(transfer_values)):
            transfer_values_flatten[i,:] =  transfer_values[i,:,:,:].flatten()


        transfer_values = transfer_values_flatten

        features_shape = (transfer_values.shape[0], transfer_values.shape[1] + NUM_CLASSES + MAX_CLASS_IDENTIFIER)
        features = np.zeros(shape=features_shape, dtype=np.float32)
        features[:, 0:transfer_values.shape[1]] = transfer_values
        features[:, transfer_values.shape[1]:transfer_values.shape[1] + NUM_CLASSES] = predictions

        for i in range(len(features)):
            argmax_class = np.argmax(features[i, transfer_values.shape[1]:transfer_values.shape[1] + NUM_CLASSES])
            amax_class = np.amax(features[i, transfer_values.shape[1]:transfer_values.shape[1] + NUM_CLASSES])
            if((argmax_class == 1 and amax_class >= TRESHOLD_1 ) or
               (argmax_class == 0 and amax_class >= TRESHOLD_0 )):
                features[i, -2] = argmax_class
                features[i, -1] = amax_class
            else:
                features[i, -2] = -5.0
                features[i, -1] = -10.0

        # print('---analysis----')
        # print(features.shape)
        # print('tranfer_values', features[-1,0:transfer_values.shape[1]])
        # print('predictions' , features[-1,transfer_values.shape[1]:transfer_values.shape[1] + NUM_CLASSES])
        # print('argmax_class', features[-1, -2])
        # print('amax_class', features[-1, -1])
        # print(patient_id, "min:", np.min(features[:,0:-7]))
        # print(patient_id, "max:", np.max(features[:,0:-7]))


        num_0 = 0
        num_1 = 0


        for i in range(0, transfer_values.shape[0]):
            if (features[i, -2] == 0.0):
                num_0 = num_0 + 1

            if (features[i, -2] == 1.0):
                num_1 = num_1 + 1


        # print(patient_id, num_0, num_1)

        # features_shape_0 = (num_0, transfer_values.shape[1] + NUM_CLASSES + MAX_CLASS_IDENTIFIER)
        # features_0 = np.zeros(shape=features_shape_0, dtype=np.float32)

        features_shape_1 = (num_1, transfer_values.shape[1] + NUM_CLASSES + MAX_CLASS_IDENTIFIER)
        features_1 = np.zeros(shape=features_shape_1, dtype=np.float32)

        # index0 = 0
        index1 = 0


        for i in range(0, transfer_values.shape[0]):
            # if (features[i, -2] == 0.0):
            #     features_0[index0] = features[i,:]
            #     index0 = index0 + 1

            if (features[i, -2] == 1.0):
                features_1[index1] = features[i,:]
                index1 = index1 + 1


        # print('--construction---')
        # print(features_0.shape, features_1.shape, features_2.shape, features_3.shape)
        # print(len(features_0), len(features_1), len(features_2), len(features_3) )
        # print( features_1.shape)
        # print('pre-sort')
        # print(features_0.shape, features_1.shape, features_2.shape, features_3.shape)
        # print(features_3[:, 512:518])

        # Sorting in descending order because want to get the most confident predictions in the smallest bin
        # features_0 = features_0[features_0[:,-1].argsort()[::-1]]
        features_1 = features_1[features_1[:,-1].argsort()[::-1]]
        # features_2 = features_2[features_2[:,-1].argsort()[::-1]]
        # features_3 = features_3[features_3[:,-1].argsort()[::-1]]


        # #class_0
        # bin_size_0 = math.ceil(features_0.shape[0]/NUM_BINS_0)
        # features_bin_0_shape = (NUM_BINS_0, transfer_values.shape[1] + NUM_CLASSES + MAX_CLASS_IDENTIFIER)
        # features_bin_0 = np.zeros(shape=features_bin_0_shape, dtype=np.float32)
        # start_index_0 = 0
        # for i in range(len(features_bin_0)):
        #     if start_index_0 >= len(features_0):
        #         features_bin_0[i,:] = 0.0
        #     else:
        #         features_bin_0[i,:] = np.mean(features_0[start_index_0:start_index_0 + bin_size_0,:], axis=0)
        #     start_index_0 = start_index_0 + bin_size_0


        #class_1
        bin_size_1 = math.ceil(features_1.shape[0]/NUM_BINS_1)
        features_bin_1_shape = (NUM_BINS_1, transfer_values.shape[1] + NUM_CLASSES + MAX_CLASS_IDENTIFIER)
        features_bin_1 = np.zeros(shape=features_bin_1_shape, dtype=np.float32)
        start_index_1 = 0
        for i in range(len(features_bin_1)):
            if start_index_1 >= len(features_1):
                features_bin_1[i,:] = 0.0
            else:
                features_bin_1[i,:] = np.mean(features_1[start_index_1:start_index_1 + bin_size_1,:], axis=0)
            start_index_1 = start_index_1 + bin_size_1


        # print("class 3", features_3.shape[0]/NUM_BINS_3 , math.ceil(features_3.shape[0]/NUM_BINS_3) )


        # print('--binned---')
        # print(features_bin_0.shape, features_bin_1.shape, features_bin_2.shape, features_bin_3.shape)

        # print('-----pre-binning')
        # # print(features_0[:, 512:518])
        # # print(features_1[:, 512:518])
        # # print(features_2[:, 512:518])
        # print(features_3[:, -6:-1])

        # print('-----post-binning')
        # # print(features_bin_0[:, 512:518])
        # # print(features_bin_1[:, 512:518])
        # # print(features_bin_2[:, 512:518])
        # print(features_bin_3[:, -6:-1])

        # print('shape', features_bin_3.shape)
        # # f.close()


        # features_flattened = np.concatenate((features_bin_0, features_bin_1), axis = 0)
        features_flattened = features_bin_1.flatten()


        # print('post flattening')
        # print(patient_id, "min:", np.min(features_flattened))
        # print(patient_id, "max:", np.max(features_flattened))

        input_features_flattened_dims = features_flattened.flatten().shape[0]
        input_features[patient_id] = features_flattened.flatten()
        count = count + 1
        print('Loaded data for patient {}/{}'.format(count, num_patients))

    return input_features_flattened_dims, input_features

def train_xgboost(trn_x, val_x, trn_y, val_y):
    clf = xgb.XGBRegressor(max_depth=5,
                           gamma=0.5,
                           objective="binary:logistic",
                           n_estimators=2500,
                           min_child_weight=96,
                           learning_rate=0.03757,
                           nthread=8,
                           subsample=0.80,
                           colsample_bytree=0.90,
                           seed=79,
                           max_delta_step=1,
                           reg_alpha=0.1,
                           reg_lambda=0.5)
    clf.fit(trn_x, trn_y, eval_set=[(val_x, val_y)], verbose=True, eval_metric='logloss', early_stopping_rounds=500)
    return clf

def make_submission():
    print('Loading data..')
    time0 = time.time()
    patient_ids = set()
    for file_path in glob.glob(DATA_PATH + "*_transfer_values.npy"):
        filename = os.path.basename(file_path)
        patient_id = re.match(r'([a-f0-9].*)_transfer_values.npy', filename).group(1)
        patient_ids.add(patient_id)

    sample_submission = pd.read_csv(STAGE2_SUBMISSION)
    defective_patients = pd.read_csv(DEFECTIVE_PATIENTS)
    #df = pd.merge(sample_submission, patient_ids_df, how='inner', on=['id'])
    test_patient_ids = set(sample_submission['id'].tolist())
    defective_patients_ids = set(defective_patients['id'].tolist())
    train_patient_ids = patient_ids.difference(test_patient_ids)
    train_patient_ids = train_patient_ids.difference(defective_patients_ids)

    train_dims, train_inputs = get_patient_features(train_patient_ids)
    train_labels = get_patient_labels(train_patient_ids)

    num_patients = len(train_patient_ids)
    X = np.ndarray(shape=(num_patients, train_dims), dtype=np.float32)
    Y = np.ndarray(shape=(num_patients), dtype=np.float32)
    count = 0
    for key in train_inputs.keys():
        X[count] = train_inputs[key]
        Y[count] = train_labels[key]
        count = count + 1

    print('Loaded train data for {} patients'.format(count))
    print("Total time to load data: " + str(timedelta(seconds=int(round(time.time() - time0)))))
    print('\nSplitting data into train, validation')
    train_x, validation_x, train_y, validation_y = model_selection.train_test_split(X, Y, random_state=42, stratify=Y, test_size=0.20)

    del X
    del Y

    print('train_x: {}'.format(train_x.shape))
    print('validation_x: {}'.format(validation_x.shape))
    print('train_y: {}'.format(train_y.shape))
    print('validation_y: {}'.format(validation_y.shape))

    print('\nTraining..')
    clf = train_xgboost(train_x, validation_x, train_y, validation_y)

    print('\nPredicting on validation set')
    validation_y_predicted = clf.predict(validation_x)
    validation_log_loss = sklearn.metrics.log_loss(validation_y, validation_y_predicted, eps=1e-15)
    print('Post-trian validation log loss: {}'.format(validation_log_loss))

    del train_x, train_y, validation_x, validation_y
    #print(validation_y)
    #print(validation_y_predicted)

    num_patients = len(test_patient_ids)
    test_dims, test_inputs = get_patient_features(test_patient_ids)

    timestamp = str(int(time.time()))
    filename = OUTPUT_PATH + 'submission-' + timestamp + ".csv"

    with open(filename, 'w') as csvfile:
        submission_writer = csv.writer(csvfile, delimiter=',')
        submission_writer.writerow(['id', 'cancer'])

        print('\nPredicting on test set')
        for key in test_inputs.keys():
            x = test_inputs[key]
            x = x.reshape((1,-1))
            y = clf.predict(x)

            submission_writer.writerow([key, y[0]])

    print('Generated submission file: {}'.format(filename))

if __name__ == '__main__':
    start_time = time.time()
    OUTPUT_PATH = '/kaggle/dev/data-science-bowl-2017-data/submissions/'
    DATA_PATH = '/kaggle_3/all_stage_features_segmented/'
    LABELS = '/kaggle/dev/data-science-bowl-2017-data/all_labels.csv'
    STAGE2_SUBMISSION = '/kaggle/dev/data-science-bowl-2017-data/stage2_sample_submission.csv'
    DEFECTIVE_PATIENTS = '/kaggle/dev/jovan/data-science-bowl-2017/data-science-bowl-2017/defective_patients.csv'
    NUM_CLASSES = 2

    make_submission()
    end_time = time.time()
    print("Total Time usage: " + str(timedelta(seconds=int(round(end_time - start_time)))))
