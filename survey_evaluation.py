#!/usr/bin/env python

import email, poplib
from email.header import decode_header
from bs4 import BeautifulSoup
import re
import argparse
import sys
from statistics import mean
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_pdf import PdfPages
from pyphen import Pyphen

#set up script params
desc = ('Get evaluation data from your mail server and writes results to a '
    'file as well as plotted results to pdf files. If you do not need one of '
    'these file types, set -notxt, -nobar, -nopie flags as desired. If your '
    'mail server is not web.de or your subject is no longer "Evaluation", '
    'make sure to set --pop_server and --subject to fitting values.')
parser = argparse.ArgumentParser(description=desc)
parser.add_argument('login', type=str, help='Your email login')
parser.add_argument('password', type=str,
                    help='The password for your email account')
parser.add_argument('--pop_server', type=str,
                    help='The POP3 server address of your mail server')
parser.add_argument('--subject', type=str,
                    help='E-Mail subject related to survey mails')
parser.add_argument('-notxt', action='store_true',
                    help='Disable saving of results to txt file')
parser.add_argument('-nobar', action='store_true',
                    help='Disable plotting of bar plots')
parser.add_argument('-nopie', action='store_true',
                    help='Disable plotting of pie plots')
args = parser.parse_args()

### CONFIG - SET VARIABLES AND DEFAULTS HERE ###
#pyphen dictionary
german_dict = Pyphen(lang='de_DE')
#e-mail information
login = args.login
password = args.password
pop_server = (args.pop_server if args.pop_server else 'pop3.web.de')
filter_subject = (args.subject if args.subject else 'Evaluation')
#file information
write_txt = not args.notxt
write_bars = not args.nobar
write_pies = not args.nopie
txt_file_name = 'results.txt'
bar_file_name = 'result_bars.pdf'
pie_file_name = 'result_pies.pdf'
#allowed text lengths until new line for plot labels
pie_wrap_len = 19
bar_wrap_len = 10
#used colors for different plot sizes
colors_simple = ['red', 'royalblue']
colors_five = ['red', 'darkorange', 'gold', 'limegreen', 'royalblue']
colors_ten = ['red', 'darkorange', 'gold', 'yellowgreen', 'limegreen',
              'deepskyblue', 'royalblue', 'navy', 'purple', 'darkmagenta']
#used font sizes in plots
text_size = 12
title_size = 14
tick_size = 10 #size of axes tick labels
pie_num_size = 10 #size of counts inside pie chart
### CONFIG END ###

#set pyplot font sizes to config values
plt.rc('font', size=text_size)
plt.rc('axes', titlesize=title_size)
plt.rc('xtick', labelsize=tick_size)
plt.rc('ytick', labelsize=tick_size)

#establish server connection
mail_box = None
try:
    mail_box = poplib.POP3_SSL(pop_server)
    mail_box.user(login)
    mail_box.pass_(password)
except Exception as err:
    print('Login failed:', err)
    exit(1)
print('Connected to mail server...')

#prepare to gather results in dict and mark numerical questions
results = {}
number_questions = set()
def check_uint(s):
    res = {
        'success': True,
        'value': None,
    }
    try:
        i = int(s)
        if i < 0:
            res['success'] = False
        else:
            res['value'] = i
    except ValueError:
        res['success'] = False
    return res
    
def make_entry(key, val):
    if not key in results:
        results[key] = []
    is_number_question = True
    for entry in val:
        if is_number_question:
            uint_info = check_uint(entry)
            if uint_info['success']:
                entry = uint_info['value']
            else:
                is_number_question = False
        results[key].append(entry)
    if is_number_question:
        number_questions.add(key)

#fetch data from mails and write progress to stdout
num_messages = len(mail_box.list()[1])
print('Checking mails:')
for i in range(num_messages):
    #notify progress
    done_str = 'Done: {}/{}'.format(i+1, num_messages)
    sys.stdout.write(done_str)
    sys.stdout.flush()
    sys.stdout.write('\b' * len(done_str))
    
    #get email html content
    try:
        raw_email  = b"\n".join(mail_box.retr(i+1)[1])
        msg = email.message_from_bytes(raw_email)
        subject = decode_header(msg['Subject'])[0][0]
        if (subject != filter_subject):
            continue
        content = msg.get_payload(decode=True)
        content = content.decode('utf-8')
        
        #extract questions and answers from html content
        questions = []
        answers = []
        soup = BeautifulSoup(content, 'html.parser')
        wrapper = soup.find(class_='mcnTextContent')
        tds = wrapper.find_all('td')
    except:
        continue
    #get individual questions and answers based on exact td content
    for answer in tds:
        q_answers = []
        for part in answer.contents:
            part = str(part)
            if part == '<br/>':
                continue
            #check if m is question
            m = re.search('^<strong>(.*)<\/strong>$', part)
            if m:
                questions.append(m.group(1))
                continue
            #check if pure number answer
            m = re.search('^vergebene Punkte: (.*) \(0 min \/ 10 max\)$', part)
            if m:
                q_answers.append(m.group(1))
                continue
            #default: regular text answer
            q_answers.append(part.strip())
        if (len(q_answers)):
            answers.append(q_answers)
    #sanity check, then make result entry
    q_len = len(questions)
    if (q_len != len(answers)):
        continue
    for i in range(q_len):
        make_entry(questions[i], answers[i])
sys.stdout.write('All done.\n')
sys.stdout.flush()

#transform results to wanted (sorted by occurence) output format
sorted_results = {}
for question, answers in results.items():
    counts = {}
    for answer in answers:
        if not answer in counts:
            counts[answer] = 1
        else:
            counts[answer] += 1
    sorted_answers = sorted(counts.items(), key=lambda kv: kv[1],
                           reverse = True)
    sorted_results[question] = sorted_answers
#get averages for purely numerical questions
means = {}
for question, answers in results.items():
    if question in number_questions:
        means[question] = round(mean(answers), 2)
def get_means_str(question):
    return 'Ø: {}'.format(means[question])

#prepare writing to txt file
def write_qa(res_file, question, sorted_counts):
    res_file.write('Frage: {}\n'.format(question))
    res_file.write('Antworten:\n')
    if question in means:
        res_file.write('\t{}\n'.format(get_means_str(question)))
    for answer, times in sorted_counts:
        res_file.write('\t{} (x{})\n'.format(answer, times))
    res_file.write('\n')
    
#prepare fetching of correct color
def get_colors(nr_answers):
    if nr_answers <= 2:
        return colors_simple
    elif nr_answers <= 5:
        return colors_five
    else:
        return colors_ten

#prepare wrapping of words with hyphenation - fails on very short line_len
def wrap_word(full_str, line_len):
    if not isinstance(full_str, str):
        return full_str
    words = full_str.split()
    lines = []
    cur_line = ''
    #for adding word parts at beginning of words
    def extend_nw(part):
        nonlocal cur_line
        if (len(cur_line) + len(part) > line_len):
            lines.append(cur_line)
            cur_line = part
        else:
            cur_line += part
    #for adding word parts in middle of word
    def extend(part):
        nonlocal cur_line
        #+1 to account for hyphen
        if len(cur_line) + len(part) +1 > line_len:
            cur_line += '-'
            lines.append(cur_line)
            cur_line = part
        else:
            cur_line += part
    #wrap creation
    for word in words:
        positions = german_dict.positions(word)
        if (len(positions) == 0):
            extend_nw(word)
            cur_line += ' '
            continue
        cursor_1 = 0
        cursor_2 = positions[0]
        extend_nw(word[cursor_1:cursor_2])
        for i in range(1, len(positions)):
            cursor_1 = cursor_2
            cursor_2 = positions[i]
            extend(word[cursor_1:cursor_2])
        extend(word[cursor_2:len(word)])
        cur_line += ' '
    lines.append(cur_line)
    lines = [l.rstrip() for l in lines]
    return '\n'.join(lines)
    
#prepare different plot functions
def plot_bars(question, ratings, labels):
    labels = [wrap_word(l, bar_wrap_len) for l in labels]
    nr_answers = len(labels)
    x = [i for i in range(nr_answers)]
    fig, axis = plt.subplots()
    axis.yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    plt.bar(x, ratings, color=get_colors(nr_answers))
    plt.xticks(x, labels)
    if question in means:
        plt.text(0.83, 0.85, get_means_str(question),
                 transform=plt.gcf().transFigure)
    plt.title(question)
    plt.tight_layout()
    
def plot_pie(question, ratings, labels):
    labels = [wrap_word(l, pie_wrap_len) for l in labels]
    total = sum(ratings)
    plt.pie(ratings, labels=labels, colors=get_colors(len(labels)),
            autopct=lambda p: '{:.0f}'.format(p * total / 100),
            textprops={'fontsize': pie_num_size})
    if question in means:
        plt.text(0.85, 0.1, get_means_str(question),
                 transform=plt.gcf().transFigure)
    plt.title(question)
    plt.tight_layout()

def start_write_plot_to_pdf():
    plt.figure()

def end_write_plot_to_pdf(pdf):
    pdf.savefig() # saves the current figure into a single pdf page
    plt.close()

#write questions + answers to simple .txt file if so desired
if write_txt:
    print('Writing results to {}...'.format(txt_file_name))
    try:
        with open(txt_file_name, 'w', encoding='utf8') as res_file:
            for question, sorted_answers in sorted_results.items():
                write_qa(res_file, question, sorted_answers)
            print('Done.')
    except:
        print('Could not write txt file. Check if some other program '
            'forbids access')
    
#create bar graph pdf file if so desired
if write_bars:
    print('Creating bar plots in file {}...'.format(bar_file_name))
    try:
        with PdfPages(bar_file_name) as pdf:
            for question, sorted_answers in sorted_results.items():
                labels = [label[0] for label in sorted_answers]
                ratings = [label[1] for label in sorted_answers]
                start_write_plot_to_pdf()
                plot_bars(question, ratings, labels)
                end_write_plot_to_pdf(pdf)
            print('Done.')
    except:
        print('Could not write to bar plot pdf file. Maybe it is currently '
            'opened in a pdf viewer?')
        
        
#create pie graph pdf file if so desired
if write_pies:
    print('Creating pie plots in file {}...'.format(pie_file_name))
    try:
        with PdfPages(pie_file_name) as pdf:
            for question, sorted_answers in sorted_results.items():
                labels = [label[0] for label in sorted_answers]
                ratings = [label[1] for label in sorted_answers]
                start_write_plot_to_pdf()
                plot_pie(question, ratings, labels)
                end_write_plot_to_pdf(pdf)
            print('Done.')
    except Exception as e:
        print(e)
        print('Could not write to pie plot pdf file. Maybe it is currently '
            'opened in a pdf viewer?')

#close open connection, finish up
mail_box.quit()
print('All done. Exit.')
