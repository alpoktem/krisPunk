# Creates a sequence of features given feature files of ted corpus
from __future__ import print_function
from optparse import OptionParser
import os
import sys
import re
import csv
import cPickle
from random import randint
from collections import OrderedDict
import numpy as np

csv.field_size_limit(1000000000000) 

features_f0_header = 'mean.normF0\tsd.normF0\tmax.normF0\tmin.normF0\tmedian.normF0\tq1.normF0\tq2.5.normF0\tq5.normF0\tq25.normF0\tq75.normF0\tq95.normF0\tq97.5.normF0\tq99.normF0\tslope.normF0\tintercept.normF0\tmean.normF0.slope\tsd.normF0.slope\tmax.normF0.slope\tmin.normF0.slope\tmedian.normF0.slope\tq1.normF0.slope\tq2.5.normF0.slope\tq5.normF0.slope\tq25.normF0.slope\tq75.normF0.slope\tq95.normF0.slope\tq97.5.normF0.slope\tq99.normF0.slope\tslope.normF0.slope\tintercept.normF0.slope'
features_i0_header = 'mean.normI0\tsd.normI0\tmax.normI0\tmin.normI0\tmedian.normI0\tq1.normI0\tq2.5.normI0\tq5.normI0\tq25.normI0\tq75.normI0\tq95.normI0\tq97.5.normI0\tq99.normI0\tslope.normI0\tintercept.normI0\tmean.normI0.slope\tsd.normI0.slope\tmax.normI0.slope\tmin.normI0.slope\tmedian.normI0.slope\tq1.normI0.slope\tq2.5.normI0.slope\tq5.normI0.slope\tq25.normI0.slope\tq75.normI0.slope\tq95.normI0.slope\tq97.5.normI0.slope\tq99.normI0.slope\tslope.normI0.slope\tintercept.normI0.slope'

SPACE = "_"
PUNCTUATION_VOCABULARY = {0:SPACE, 1:',', 2:'.', 3:'?', 4:'!', 5:'-', 6:';', 7:':'}
INV_PUNCTUATION_CODES = {SPACE:0, ',':1, '.':2, '?':3, '!':4, '-':5, ';':6, ':':7, '':0}
REDUCED_PUNCTUATION_VOCABULARY = {0:SPACE, 1:',', 2:'.', 3:'?'}
REDUCED_INV_PUNCTUATION_CODES = {SPACE:0, ',':1, '.':2, '?':3, '':0}
EOS_PUNCTUATION_CODES = [2,3,4,5,6,7]

FLOAT_FORMATTING="{0:.4f}"
END_TOKEN = "<END>" 


def puncProper(punc):
	if punc in INV_PUNCTUATION_CODES.keys():
		return punc
	else:
		return puncEstimate(punc)

def reducePuncCode(puncCode):
	if puncCode in [4, 5, 6, 7]: #period
		return 2
	else:
		return puncCode

def reducePunc(punc):
	puncCode = INV_PUNCTUATION_CODES[punc]
	reducedPuncCode = reducePuncCode(puncCode)
	return PUNCTUATION_VOCABULARY[reducedPuncCode]

def puncEstimate(punc):
	if '.' in punc:
		return '.'
	elif ',' in punc:
		return ','
	elif '?' in punc:
		return '?'
	elif '!' in punc:
		return '!'
	elif ':' in punc:
		return ':'
	elif ';' in punc:
		return ';'
	elif '-' in punc:
		return '-'
	else:
		return ''

def checkFile(filename, variable):
    if not filename:
        sys.exit("%s file not given"%variable)
    else:
        if not os.path.isfile(filename):
            sys.exit("%s file %s does not exist"%(variable, filename))

def checkFolder(dir, variable):
	if not os.path.exists(dir):
		sys.exit("%s directory not given"%variable)

def readTedDataToMemory(file_wordalign, file_wordaggs_f0, file_wordaggs_i0, dir_raw_f0=None, dir_raw_i0=None):

	#read wordaggs_f0 file to a dictionary 
	word_id_to_f0_features_dic = {}
	at_header_line = 1
	with open(file_wordaggs_f0, 'rt') as f:
		reader = csv.reader(f, delimiter=' ', quotechar=None)
		for row in reader:
			if at_header_line:
				at_header_line = 0
			else:
				word_id_to_f0_features_dic[row[0]] = row[6:36]

	#read wordaggs_i0 file to a dictionary
	word_id_to_i0_features_dic = {}
	at_header_line = 1
	with open(file_wordaggs_i0, 'rt') as f:
		reader = csv.reader(f, delimiter=' ', quotechar=None)
		for row in reader:
			if at_header_line:
				at_header_line = 0
			else:
				word_id_to_i0_features_dic[row[0]] = row[6:36]

	#read aligned word file to a dictionary (word.align)
	word_data_aligned_dic = OrderedDict()
	with open(options.file_wordalign, 'rt') as f:
		reader = csv.reader(f, delimiter='\t', quotechar=None)
		first_line = 1
		for row in reader:
			if first_line:
				first_line = 0
				continue
			word_data_aligned_dic[row[7]] = [[row[5], row[6], row[9]]] #starttime, endtime, word


	return [word_id_to_f0_features_dic, word_id_to_i0_features_dic, word_data_aligned_dic]

def featureVectorToFloat(featureVector):
	features_fixed = [0.0] * len(featureVector)
	for ind, val in enumerate(featureVector):
		if val == 'NA':
			features_fixed[ind] = 0.0
		else:
			features_fixed[ind] = float(FLOAT_FORMATTING.format(float(val)))
	return features_fixed

def structureData(word_id_to_f0_features_dic, word_id_to_i0_features_dic, word_data_aligned_dic, word_id_to_raw_f0_features_dic=None, word_id_to_raw_i0_features_dic=None):
	structured_data = []
	sum_speech_rate_phon = 0.0
	sum_speech_rate_syll = 0.0
	count_speech_rate_syll = 0
	count_speech_rate_phon = 0

	prev_wordEntry = {'starttime':0.0, 'endtime':0.0, 'punc_before':"", 'punc_after':"", 
					  'features_f0':[0],
					  'features_i0':[0]}
	for key in word_data_aligned_dic:
		#case of it's that's
		if len(word_data_aligned_dic[key]) == 2 and re.search(r"^{", word_data_aligned_dic[key][1][2]):
			word_data_aligned_dic[key][0][2] += "'" + word_data_aligned_dic[key][1][2][1:]
			word_data_aligned_dic[key][0][4] = word_data_aligned_dic[key][1][4]
			del word_data_aligned_dic[key][1]

		for word_index, word_data in enumerate(word_data_aligned_dic[key]):
			wordEntry = {'sent.id':"", 'word.id':"", 'word.id.simple':"", 'word':"", 
					     'word.stripped':"", 'utt_pos':"", 'punc_before':"", 'punc_after':"", 'total_punc_before':"",
					     'minimal_punc_before': "", 'starttime':0.0, 'endtime':0.0, 'starttime.approx':0, 
					     'endtime.approx':0, 'features_f0':[0], 'pause_before_dur':0.0, 
					     'features_i0':[0], 'mean.f0_jump_from_prev':0.0, 'mean.i0_jump_from_prev':0.0,
					     'range.f0':0.0, 'range.i0':0.0, 'word_dur':0.0,
					     'speech.rate.syll': 0.0, 'speech.rate.phon':0.0}
			wordEntry['word.id'] = key
			word_stripped = word_data[2]

			if not word_data[0] == "NA": 
				wordEntry['starttime'] = float(word_data[0])
			else:
				wordEntry['starttime'] = -1
			if not word_data[1] == "NA": 
				wordEntry['endtime'] = float(word_data[1])
			else:
				wordEntry['endtime'] = -1

			if re.search(r"\w", word_stripped) == None:
				continue

			#strip word from non-word stuff at the beginning and end
			word_stripped = word_stripped[re.search(r"\w", word_stripped).start():]
			word_stripped = word_stripped[::-1]
			word_stripped = word_stripped[re.search(r"\w", word_stripped).start():]
			word_stripped = word_stripped[::-1]

			wordEntry['word'] += word_stripped
			wordEntry['word.stripped'] += word_stripped

			try:
				wordEntry['features_f0'] = word_id_to_f0_features_dic[wordEntry['word.id']]
			except Exception as e:
				wordEntry['features_f0'] = [0] * 29
			
			try:
				wordEntry['features_i0'] = word_id_to_i0_features_dic[wordEntry['word.id']]
			except Exception as e:
				wordEntry['features_i0'] = [0] * 29
			
			#pause values
			if not wordEntry['starttime'] == -1 and not prev_wordEntry['endtime'] == -1:
				diff = wordEntry['starttime'] - prev_wordEntry['endtime']
			else:
				diff = 0.0
			wordEntry['pause_before_dur'] = float(FLOAT_FORMATTING.format(diff))

			#word duration
			if not wordEntry['starttime'] == -1 and not prev_wordEntry['endtime'] == -1:
				diff = wordEntry['endtime'] - wordEntry['starttime']
			else:
				diff = 0.0
			wordEntry['word_dur'] = float(FLOAT_FORMATTING.format(diff))

			#speech rate with respect to syllables
			# no_syllables = float(tools.sylco(wordEntry['word.stripped']))
			# if not no_syllables == 0: wordEntry['speech.rate.syll'] = float(FLOAT_FORMATTING.format(wordEntry['word_dur'] / no_syllables))

			# if not wordEntry['speech.rate.syll'] == 0:
			# 	sum_speech_rate_syll += wordEntry['speech.rate.syll']
			# 	count_speech_rate_syll += 1

			#speech rate with respect to phonemes (no of characters)
			no_of_characters = len(re.sub('[^a-zA-Z]','',wordEntry['word']))
			speech_rate_phon = wordEntry['word_dur'] / no_of_characters
			wordEntry['speech.rate.phon'] = float(FLOAT_FORMATTING.format(speech_rate_phon))

			if wordEntry['speech.rate.phon'] > 0:
				sum_speech_rate_phon += wordEntry['speech.rate.phon']
				count_speech_rate_phon += 1

			#convert i0 and f0 feature vectors to float vectors
			wordEntry['features_f0'] = featureVectorToFloat(wordEntry['features_f0'])
			wordEntry['features_i0'] = featureVectorToFloat(wordEntry['features_i0'])

			#other prosodic features
			#jump.f0 = mean.f0 of the current word - mean.f0 of the previous word
			f0_jump = wordEntry['features_f0'][0] - prev_wordEntry['features_f0'][0]
			wordEntry['mean.f0_jump_from_prev'] = float(FLOAT_FORMATTING.format(f0_jump))
			#jump.i0 = mean.i0 of the current word - mean.i0 of the previous word
			i0_jump = wordEntry['features_i0'][0] - prev_wordEntry['features_i0'][0]
			wordEntry['mean.i0_jump_from_prev'] = float(FLOAT_FORMATTING.format(i0_jump))
			#range.f0 = max.f0 - min.f0
			f0_range = wordEntry['features_f0'][2] - wordEntry['features_f0'][3]
			wordEntry['range.f0'] = float(FLOAT_FORMATTING.format(f0_range))
			#range.i0 = max.i0 - min.i0
			i0_range = wordEntry['features_i0'][2] - wordEntry['features_i0'][3]
			wordEntry['range.i0'] = float(FLOAT_FORMATTING.format(i0_range))

			# #check punctuation marks
			# word_being_processed = wordEntry['word']
			# punc_after = ""
			# punc_before = ""

			# #check beginning
			# if re.search(r"^\W", word_being_processed) and word_index == 0:
			# 	punc = word_being_processed[:re.search(r"\w", word_being_processed).start()]
			# 	punc_before += punc
			# 	word_being_processed = word_being_processed[re.search(r"\w", word_being_processed).start():]

			# #check end again (issue with quotations)
			# word_reversed = word_being_processed[::-1]
			# if re.search(r"^\W",word_reversed) and word_index == len(word_data_aligned_dic[key]) - 1:
			# 	punc = word_reversed[:re.search(r"\w", word_reversed).start()][::-1]
			# 	punc_after = punc + punc_after
			# 	word_being_processed = word_reversed[re.search(r"\w", word_reversed).start():][::-1]

			# wordEntry['punc_before'] = punc_before
			# wordEntry['punc_after'] = punc_after

			# total_punc_before = prev_wordEntry['punc_after'] + wordEntry['punc_before']

			# wordEntry['total_punc_before'] = total_punc_before
			# wordEntry['minimal_punc_before'] = puncProper(total_punc_before)

			structured_data += [wordEntry]
			prev_wordEntry = wordEntry

	avg_speech_rate = sum_speech_rate_phon / count_speech_rate_phon
	return structured_data, avg_speech_rate

def word_data_to_pickle(talk_data, output_pickle_file):
	with open(output_pickle_file, 'wb') as f:
		cPickle.dump(talk_data, f, cPickle.HIGHEST_PROTOCOL)

def word_data_to_csv(talk_data, output_csv_file):
	with open(output_csv_file, 'wb') as f:
		w = csv.writer(f, delimiter="\t")
		rowIds = ['word', 'punctuation', 'word.duration', 'speech.rate.norm', 'pause', 'mean.f0', 'range.f0', 'mean.i0', 'range.i0']
		w.writerow(rowIds)
		rows = zip( talk_data[rowIds[0]],
					talk_data[rowIds[1]],
					talk_data[rowIds[2]],
					talk_data[rowIds[3]],
					talk_data[rowIds[4]],
					talk_data[rowIds[5]],
					talk_data[rowIds[6]],
					talk_data[rowIds[7]],
					talk_data[rowIds[8]])
		for row in rows:                                        
			w.writerow(row) 

def convert_value_to_level(pause_dur, pause_bins):
	level = 0
	for bin_no, bin_upper_limit in enumerate(pause_bins):
		if pause_dur > bin_upper_limit:
			level += 1
		else:
			break
	return level

def create_pause_bins():
	bins = np.arange(0, 1, 0.05)
	bins = np.concatenate((bins, np.arange(1, 2, 0.1)))
	bins = np.concatenate((bins, np.arange(2, 5, 0.2)))
	bins = np.concatenate((bins, np.arange(5, 10, 0.5)))
	bins = np.concatenate((bins, np.arange(10, 20, 1)))
	return bins

def create_semitone_bins():
	bins = np.arange(-20, -10, 1)
	bins = np.concatenate((bins, np.arange(-10, -5, 0.5)))
	bins = np.concatenate((bins, np.arange(-5, 0, 0.25)))
	bins = np.concatenate((bins, np.arange(0, 5, 0.25)))
	bins = np.concatenate((bins, np.arange(5, 10, 0.5)))
	bins = np.concatenate((bins, np.arange(10, 20, 1)))
	return bins

def wordDataToDictionary(structured_word_data, avg_speech_rate):
	actualword_seq = []
	#speech_rate_syll_seq = []
	speech_rate_phon_seq = []
	speech_rate_normalized_seq = []
	word_dur_seq = []
	punc_seq = []
	punc_reduced_seq = []
	pause_before_seq = []
	meanf0_seq = []
	medf0_seq = []
	meani0_seq = []
	slopef0_seq = []
	sdf0_seq = []
	jumpf0_seq = []
	jumpi0_seq = []
	rangef0_seq = []
	rangei0_seq = []
	#id sequences
	meanf0_id_seq = []
	meani0_id_seq = []
	rangef0_id_seq = []
	rangei0_id_seq = []
	pause_id_seq = []
	punctuation_id_seq = []
	reduced_punctuation_id_seq = []

	pause_bins = create_pause_bins()
	semitone_bins = create_semitone_bins()

	for word_datum in structured_word_data:
		actualword_seq += [word_datum['word']]
		word_dur_seq += [word_datum['word_dur']]
		punc_seq += [word_datum['minimal_punc_before']]
		punc_reduced_seq += [reducePunc(word_datum['minimal_punc_before'])]
		pause_before_seq += [word_datum['pause_before_dur']]
		meanf0_seq += [word_datum['features_f0'][0]]
		meani0_seq += [word_datum['features_i0'][0]]
		sdf0_seq += [word_datum['features_f0'][1]]
		medf0_seq += [word_datum['features_f0'][4]]
		slopef0_seq += [word_datum['features_f0'][14]]
		jumpf0_seq += [word_datum['mean.f0_jump_from_prev']]
		jumpi0_seq += [word_datum['mean.i0_jump_from_prev']]
		rangef0_seq += [word_datum['range.f0']]
		rangei0_seq += [word_datum['range.i0']]
		#id sequences
		meanf0_id_seq += [convert_value_to_level(word_datum['features_f0'][0], semitone_bins)]
		meani0_id_seq += [convert_value_to_level(word_datum['features_i0'][0], semitone_bins)]
		rangef0_id_seq += [convert_value_to_level(word_datum['range.f0'], semitone_bins)]
		rangei0_id_seq += [convert_value_to_level(word_datum['range.i0'], semitone_bins)]
		pause_id_seq += [convert_value_to_level(word_datum['pause_before_dur'], pause_bins)]
		#punctuation
		punctuation_id = INV_PUNCTUATION_CODES[word_datum['minimal_punc_before']]
		punctuation_id_seq += [punctuation_id]
		reduced_punctuation_id_seq += [reducePuncCode(punctuation_id)]
		#speech rate
		#speech_rate_syll_seq += [word_datum['speech.rate.syll']]
		speech_rate_phon_seq += [word_datum['speech.rate.phon']]
		normalized_speech_rate = (word_datum['speech.rate.phon'] / avg_speech_rate)
		if not normalized_speech_rate == 0.0:
			speech_rate_normalized_seq += [float(FLOAT_FORMATTING.format(normalized_speech_rate))]
		else:
			speech_rate_normalized_seq += [1.0]


	metadata = {'no_of_semitone_levels': len(semitone_bins),
				'no_of_pause_levels': len(pause_bins),
				'no_of_words': len(actualword_seq),
				'avg_speech_rate': avg_speech_rate
	}

	talk_data = {  'word': actualword_seq,
				   'word.duration': word_dur_seq ,
				   #'speech.rate.syll' : speech_rate_syll_seq,
				   'speech.rate.phon': speech_rate_phon_seq,
				   'speech.rate.norm': speech_rate_normalized_seq ,
				   'punctuation': punc_seq,
				   'punctuation.reduced': punc_reduced_seq,
				   'pause': pause_before_seq,
				   'pause.id': pause_id_seq,
				   'mean.f0': meanf0_seq,
				   'mean.i0': meani0_seq,
				   'med.f0': medf0_seq,
				   'slope.f0': slopef0_seq,
				   'sd.f0': sdf0_seq,
				   'jump.f0': jumpf0_seq,
				   'jump.i0': jumpi0_seq ,
				   'range.f0': rangef0_seq,
				   'range.i0': rangei0_seq ,
				   'mean.f0.id': meanf0_id_seq,
				   'mean.i0.id': meani0_id_seq,
				   'range.f0.id': rangef0_id_seq,
				   'range.i0.id': rangei0_id_seq,
				   'punc.id': punctuation_id_seq,
				   'punc.red.id': reduced_punctuation_id_seq,
				   'metadata': metadata
	}
	return talk_data

def findAggsFile(working_directory, feat):
	feat_dir = os.path.join(working_directory, feat)
	if os.path.exists(feat_dir):
		for file in os.listdir(feat_dir):
			if file.endswith("aggs.txt"):
				return os.path.join(working_directory, feat, file)
	sys.exit("Cannot find %s aggs file"%feat)

def main(options):
	checkFolder(options.dir_working, "dir_working")
	checkFile(options.file_wordalign, "file_wordalign")

	file_wordaggs_f0 = findAggsFile(options.dir_working, "f0")
	print(file_wordaggs_f0)

	file_wordaggs_i0 = findAggsFile(options.dir_working, "i0")
	print(file_wordaggs_i0)

	dir_raw_f0 = os.path.join(options.dir_working, "raw-f0")
	dir_raw_i0 = os.path.join(options.dir_working, "raw-i0")

	[word_id_to_f0_features_dic, word_id_to_i0_features_dic, word_data_aligned_dic] = readTedDataToMemory(options.file_wordalign, file_wordaggs_f0, file_wordaggs_i0, dir_raw_f0, dir_raw_i0)
	[structured_word_data, avg_speech_rate] = structureData(word_id_to_f0_features_dic, word_id_to_i0_features_dic, word_data_aligned_dic)

	talk_data = wordDataToDictionary(structured_word_data, avg_speech_rate)

	dir_proscript = os.path.join(options.dir_working, "proscript")
	if not os.path.exists(dir_proscript):
		os.makedirs(dir_proscript)
	word_data_to_pickle(talk_data, os.path.join(dir_proscript, "%s.pcl"%options.id_file))
	word_data_to_csv(talk_data, os.path.join(dir_proscript, "%s.csv"%options.id_file))
	return 1

if __name__ == "__main__":
	usage = "usage: %prog [-s infile] [option]"
	parser = OptionParser(usage=usage)
	#parser.add_option("-a", "--audio", dest="file_audio", default=None, help="wav", type="string")
	parser.add_option("-l", "--align", dest="file_wordalign", default=None, help="word.txt.norm.align", type="string")	#in /txt-sent
	parser.add_option("-d", "--dir_working", dest="dir_working", default=None, help="Working directory where prosodic parameters and output is stored", type="string")
	parser.add_option("-i", "--id", dest="id_file", default="proscript", help="file id", type="string")	#in /txt-sent

	(options, args) = parser.parse_args()

	print("=====Proscripter=====")
	
	if main(options):
		print("Proscripted.")
	else:
		print("Failed.")