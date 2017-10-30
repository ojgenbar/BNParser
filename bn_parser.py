#!/usr/bin/env python
# coding: UTF-8
import urllib2
import random
import os
import time
import datetime
import cPickle
from BeautifulSoup import *
import sys
from exception_str import exception_str

from Geocoder.Geocoder import Geocoder


class BNParser:
    def __init__(self):
        # Создаем и настриваем экземпляр геокодера
        en_geo = Geocoder()
        en_geo.lang = 4
        en_geo.results = 1
        en_geo.ll = (31.293352, 60.018353)
        en_geo.spn = (10, 4)
        en_geo.rspn = '1'
        en_geo.kind = 'house'
        # Если с интернетом туго:
        # en_geo.offlineMod = True
        self.geocoder = en_geo

    def bn_resale_parser(self, infile, logpath, logs=True, txt=True, list_dump=True, returninfo=False, savecache=False):
        tstart = time.time()

        try:
            os.makedirs(logpath)
        except OSError:
            pass

        # geo_log, parse_log - лог-файлы
        geo_log_path = os.path.join(logpath, 'BNGeocodeLog.txt')
        geo_log = open(geo_log_path, 'a')
        parse_log_path = os.path.join(logpath, 'BNParseLog.txt')
        parse_log = open(parse_log_path, 'a')

        parse_log.write(time.strftime("%Y.%m.%d_%H.%M", time.gmtime(time.time() + 14400)) + '\n')
        parse_log.write('File: %s\n' % infile)

        try:
            f5 = open(infile, 'r')

            t1 = time.time() - tstart
            parse_log.write('Start - ' + str(t1) + ' sec.\n\n')

            property_list = []

            # Глобальные счетчик ошибок геокодирования
            failure_count = 0

            page = f5.read()
            bsoup = BeautifulSoup(page)
            # Возвращаем все теги строк (row tags)
            row_tags = bsoup.findAll('tr')

            # разбор HTML документа и извлечение из него квартир
            i = 3
            rooms = 1
            district = 'Адмиралтейский район'

            try:
                while i < len(row_tags) - 1:
                    i += 1
                    soup2 = row_tags[i]
                    # поиск подзаголовков.
                    # если подзаголовки есть, то программа не во внутренней таблице (см. структуру выдачи БНа)
                    thtag = soup2.findAll('th')
                    if len(thtag) != 0:
                        continue
                    # поиск ячеек в строке
                    tdtags = soup2.findAll('td')

                    if len(tdtags) == 2:
                        district = tdtags[0].string.strip()
                        continue

                    if len(tdtags) < 10:
                        continue

                    lst = []
                    if row_tags[i][u'class'] == u'bg3':
                        # Тип объявления
                        bn_type = 3
                        # Комнаты, район
                        lst.append(rooms)
                        lst.append(district)
                        # Адрес
                        workstr = tdtags[1].a.string.strip()
                        workstr_old = workstr
                        workstr = workstr.replace(u'-&shy;', u'-')
                        workstr = workstr.replace(u'Адм.', u'Адмирала')
                        try:
                            print workstr_old, '\n' + workstr + '\n'
                        except UnicodeEncodeError:
                            pass
                        lst.append(workstr)
                        address = workstr

                        # геокодирование элементов
                        if district == u'Область':
                            workstr = u' '.join([u'Ленинградская', district, address])
                        else:
                            workstr = u' '.join([district, address])
                        geo = self.geocoder.geocode(workstr)
                        if not geo.success:
                            geo_log.write('Failure:\n' + geo.message + '\n\n')
                            failure_count += failure_count
                            continue
                        # широта, долгота, адрес на английском
                        lst.append(geo.lat)
                        lst.append(geo.long)
                        lst.append(geo.address)

                        # этажность
                        lst.append(tdtags[2].string.strip().replace(u'\\', u'/'))

                        # тип здания (серия)
                        workstr = tdtags[3].contents[0].strip()

                        if (workstr == u'&nbsp') or (workstr == u'&nbsp;'):
                            lst.append(u'')
                        else:
                            if workstr != u'':
                                lst.append(workstr)
                            else:
                                lst.append((tdtags[3].a.contents[0]).strip())
                        # площадь общая
                        lst.append(float(tdtags[4].string))
                        # площадь жилая
                        if (tdtags[5].contents[0]).strip() == u'0':
                            lst.append(u'0')
                        else:
                            lst.append(tdtags[5].span.string.strip())
                        # площадь кухни
                        lst.append(tdtags[6].string.strip())
                        # тип с/у или неизвестен '?'
                        workstr = tdtags[7].string.strip()
                        if (workstr == u'&nbsp') or (workstr == u'&nbsp;'):
                            lst.append(u'?')
                        else:
                            lst.append(workstr)
                        # срок сдачи
                        lst.append(u'Вторичный')
                        # цена
                        cena_str = tdtags[8].strong.string.strip()
                        try:
                            lst.append(float(cena_str))
                        except ValueError:
                            message = 'Failure:\nThe price is not digit. The price = "%s". The address = "%s"\n\n' % \
                                      (cena_str.encode('utf-8'), address.encode('utf-8'))
                            parse_log.write(message)
                            print message
                            continue
                        # цена м2
                        try:
                            lst.append(lst[13] / float(lst[8]))
                        except ZeroDivisionError:
                            lst.append(None)
                        # доп. условия
                        workstr = ((tdtags[9]).contents[0]).strip()
                        if (workstr == u'&nbsp') or (workstr == u'&nbsp;'):
                            lst.append(u'')
                        else:
                            lst.append(((tdtags[9]).a[u'title']).strip())
                        # объявление частное или название организации
                        lst.append(((tdtags[10]).contents[0]).strip())
                        # телефон
                        lst.append(tdtags[11].string.strip())
                        # описание
                        workstr = tdtags[12].contents[0].strip()
                        if (workstr == u'&nbsp') or (workstr == u'&nbsp;'):
                            lst.append(u'')
                        else:
                            lst.append(workstr)

                        # ID, type, link
                        link = tdtags[1].a[u'href'].strip()
                        lst.append(int(link.split(u'/')[-1].split(u'.')[0]))
                        lst.append(bn_type)
                        lst.append(('/'.join(['http://www.bn.ru', link[1:]])).decode('utf8'))

                        # добавляем квартиру к имеющимся
                        property_list.append(lst)

                        continue

                    # Тип объявления
                    # bn_type = row_tags[i][u'class'].replace(u'bg', u'')
                    bn_type = row_tags[i][u'class']
                    if bn_type == u'bg1':
                        bn_type = 1
                    elif bn_type == u'bg2':
                        bn_type = 2
                    elif bn_type == u'bg_gold':
                        bn_type = 4
                    else:
                        raise Exception('Unknown ad type!')
                    # Комнаты, район
                    rooms = int(tdtags[0].string.strip())
                    lst.append(rooms)
                    lst.append(district)
                    # Адрес
                    workstr = tdtags[1].a.string.strip()
                    workstr_old = workstr
                    workstr = workstr.replace(u'-&shy;', u'-')
                    workstr = workstr.replace(u'Адм.', u'Адмирала')
                    try:
                        print workstr_old, '\n' + workstr + '\n'
                    except UnicodeEncodeError:
                        pass
                    lst.append(workstr)
                    address = workstr

                    # геокодирование элементов
                    if district == u'Область':
                        workstr = u' '.join([u'Ленинградская', district, address])
                    else:
                        workstr = u' '.join([district, address])
                    geo = self.geocoder.geocode(workstr)
                    if not geo.success:
                        geo_log.write('Failure:\n' + geo.message + '\n\n')
                        failure_count += failure_count
                        continue
                    # широта, долгота, адрес на английском
                    lst.append(geo.lat)
                    lst.append(geo.long)
                    lst.append(geo.address)

                    # этажность
                    lst.append(tdtags[2].string.strip().replace(u'\\', u'/'))

                    # тип здания (серия)
                    workstr = tdtags[3].contents[0].strip()

                    if (workstr == u'&nbsp') or (workstr == u'&nbsp;'):
                        lst.append(u'')
                    else:
                        if workstr != u'':
                            lst.append(workstr)
                        else:
                            lst.append((tdtags[3].a.contents[0]).strip())
                    # площадь общая
                    lst.append(float(tdtags[4].string))
                    # площадь жилая
                    lst.append(tdtags[5].string.strip())
                    # площадь кухни
                    lst.append(tdtags[6].string.strip())
                    # тип с/у или неизвестен '?'
                    workstr = tdtags[7].string.strip()
                    if (workstr == u'&nbsp') or (workstr == u'&nbsp;'):
                        lst.append(u'?')
                    else:
                        lst.append(workstr)
                    # срок сдачи
                    lst.append(u'Вторичный')
                    # цена
                    cena_str = tdtags[8].div.b.string.strip()
                    try:
                        lst.append(float(cena_str))
                    except ValueError:
                        message = 'Failure:\nThe price is not digit. The price = "%s". The address = "%s"\n\n' % \
                                  (cena_str.encode('utf-8'), address.encode('utf-8'))
                        parse_log.write(message)
                        print message
                        continue
                    # цена м2
                    try:
                        lst.append(lst[13] / float(lst[8]))
                    except ZeroDivisionError:
                        lst.append(None)
                    # доп. условия
                    workstr = ((tdtags[9]).contents[0]).strip()
                    if (workstr == u'&nbsp') or (workstr == u'&nbsp;'):
                        lst.append(u'')
                    else:
                        lst.append(((tdtags[9]).a[u'title']).strip())
                    # объявление частное или название организации
                    lst.append(((tdtags[10]).contents[0]).strip())
                    # телефон
                    lst.append(tdtags[11].string.strip())
                    # описание
                    workstr = tdtags[12].contents[0].strip()
                    if (workstr == u'&nbsp') or (workstr == u'&nbsp;'):
                        lst.append(u'')
                    else:
                        lst.append(workstr)

                    # ID, type, link
                    link = tdtags[1].a[u'href'].strip()
                    lst.append(int(link.split(u'/')[-1].split(u'.')[0]))
                    lst.append(bn_type)
                    lst.append(('/'.join(['http://www.bn.ru', link[1:]])).decode('utf8'))

                    # добавляем квартиру к имеющимся
                    property_list.append(lst)

            except ZeroDivisionError:
                parse_log.write('== Failure to parse ==\n')
                message = exception_str() + '\n\n'
                parse_log.write(message)
                print message

            f5.close()

            t2 = time.time() - tstart - t1

            print "Parse, Geocoding time = ", t2
            parse_log.write('Parse, Geocoding time = ' + str(t2 / 60) + ' min.\n\n')

            # Сохраняем списки с квартирами
            if list_dump:
                f = open(os.path.join(logpath, 'data2_lst'), 'wb')
                cPickle.dump(property_list, f)
                f.close()

            # Запись в текстовые файлы табличные данные квартир. Начало:
            if txt:
                s = os.path.join(logpath, 'BN_result2.txt')
                f5 = open(s, 'w')

                c = 0
                for i in property_list:
                    for j in range(0, len(property_list[c]) - 1, 1):
                        if j in (0, 3, 4, 8, 13, 14, 19, 20, 21):
                            f5.write((unicode((i[j])) + u'\t').encode('utf-8'))
                        else:
                            f5.write((i[j] + u'\t').encode('utf-8'))
                    f5.write(((i[len(property_list[c]) - 1]) + u'\n').encode('utf-8'))
                    c += 1
                f5.close()
            # Конец.

            # Сохраняем результаты геокодера
            if savecache:
                self.geocoder.saveCache()

            tend = time.time()
            twork = tend - tstart
            print "Time ", twork
            parse_log.write('____________________________\n')
            parse_log.write('Time ' + unicode(twork / 60) + '\n')
            print u'Geocoding mistakes = ', unicode(failure_count)
            print u'Quantity = ', unicode(len(property_list))
            parse_log.write('Geocoding mistakes = ' + unicode(failure_count) + '\n')
            parse_log.write('Quantity = ' + unicode(len(property_list)) + '\n')
            parse_log.write('-'*120 + '\n\n')

            # Закрываем открытые файлы
            geo_log.close()
            parse_log.close()

            if not logs:
                os.remove(parse_log_path)
                os.remove(geo_log_path)
            if returninfo:
                return property_list, failure_count
            else:
                return property_list

        except ZeroDivisionError:
            # Сохраняем геокодированные адреса
            self.geocoder.saveCache()
            exc = sys.exc_info()[0]
            print 'ой-ой! Помилка:\n%s' % exception_str()
            parse_log.write(exception_str() + '\n\n')
            raise exc

    def pocket_parse(self, folder, outpath, logs=True, txt=True, list_dump=True):

        tstart = time.time()

        # лог
        log = 'HTML directory:\n%s\nParse in:\n%s\n' % (folder, outpath)
        listings = []
        errors_count = 0

        try:
            files = [i for i in os.listdir(folder) if (os.path.splitext(i)[1].lower() == '.html') and i[:4] == 'BNp2']
            for f in files:
                message = 'Parsing "%s"\n' % f
                log += message
                print message
                new, errors = self.bn_resale_parser(
                    os.path.join(folder, f),
                    outpath,
                    logs=True,
                    txt=False,
                    list_dump=False,
                    returninfo=True)
                log += 'Quantity of flats in request = %s\n\n' % len(new)
                print
                listings += new
                errors_count += errors
                self.geocoder.saveCache()

            if list_dump:
                dumppath = os.path.join(outpath, 'BNp2_list.pd')
                f = open(dumppath, 'wb')
                cPickle.dump(listings, f)
                f.close()
                log += 'Dump path (was made): %s\n' % dumppath

            if txt:
                txtpath = os.path.join(outpath, 'BNp2_list.txt')
                self.make_txt(listings, txtpath)
                log += 'Txt table path (was made): %s\n' % txtpath

            tend = time.time()
            twork = tend - tstart
            print '____________________________'
            print "Time of parsing (all): ", twork
            print "Geocoding mistakes = ", errors_count
            print 'Quantity = ' + unicode(len(listings)) + '\n'
            log += '_'*30 + '\n'
            log += 'Time ' + unicode(twork / 60) + '\n'
            log += 'Geocoding mistakes = ' + unicode(errors_count) + '\n'
            log += 'Quantity = ' + unicode(len(listings)) + '\n'
            log += '-' * 120 + '\n\n'
        except ZeroDivisionError:
            message = '_'*30 + '\n'
            exc = exception_str()
            message += "Error has occurred!:\n%s\n\n" % exc
            print message
            log += message

        if logs:
            logpath = os.path.join(outpath, 'BNp2ParseLogAll.txt')
            open(logpath, 'w').write(log)
        self.geocoder.saveCache()
        return listings

    @staticmethod
    def make_txt(property_list, path):

        out = ''
        c = 0
        for i in property_list:
            for j in range(0, len(property_list[c]) - 1, 1):
                if j in (0, 3, 4, 8, 13, 14, 19, 20, 21):
                    out += (unicode((i[j])) + u'\t').encode('utf-8')
                else:
                    out += (i[j] + u'\t').encode('utf-8')
            out += ((i[len(property_list[c]) - 1]) + u'\n').encode('utf-8')
            c += 1
        open(path, 'w').write(out)
        return out


class BNDownloader:

    def __init__(self, path):
        basepath = os.path.dirname(__file__)
        intervals_path = os.path.join(basepath, r'BNp1Intervals.set')
        self.p1intervals = self.get_intervals(intervals_path)
        intervals_path = os.path.join(basepath, r'BNp2Intervals.set')
        self.p2intervals = self.get_intervals(intervals_path)
        intervals_path = os.path.join(basepath, r'BNpAIntervals.set')
        self.pAintervals = self.get_intervals(intervals_path)
        self.path = path

    @staticmethod
    def get_intervals(path=None):
        rows = open(path).read().strip().split('\n')
        interv = []

        for row in rows:
            start, stop, q = row.strip().split('\t')
            interv.append((int(start), int(stop)))

        return interv

    def download(self, path=None, intervals=None, supply_type=1):
        """
        Funktion for download all supply in bn.ru
        :param path: path to folder. String
        :param intervals: tuple of tuples like (1000, 2000) prices per reguest
        :param supply_type: 0 - new, 1 - resale, 2 - rent
        :return: None
        """
        tstart = time.time()
        if not path:
            path = self.path

        r = urllib2.build_opener()
        r.addheaders = [
            ('User-agent',
             'Mozilla/5.0 (X11; Linux x86_64; rv:10.0.12) Gecko/20100101 Firefox/10.0.12 Iceweasel/10.0.12'),
            ('Connection', 'keep-alive'),
            ('Accept-Language', 'ru-ru,ru;q=0.8,en-us;q=0.5,en;q=0.3'),
            ('Cache-Control', 'max-age=0'),
            ('Accept-Charset', 'utf-8;q=0.3'),
            ('Accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8')
        ]

        try:
            os.makedirs(os.path.join(path, 'HTMLs'))
        except OSError:
            pass

        supply_type = int(supply_type)

        # Choose type of supply.
        if supply_type == 1:
            baseURL = r'http://www.bn.ru/zap_fl.phtml?print=printall&'
            numtype = 2
            if not intervals:
                intervals = self.p2intervals
        elif supply_type == 0:
            baseURL = r'http://www.bn.ru/zap_bd.phtml?print=printall&'
            numtype = 1
            if not intervals:
                intervals = self.p1intervals
        elif supply_type == 2:
            baseURL = r'http://www.bn.ru/zap_ar.phtml?print=printall&'
            numtype = 'A'
            if not intervals:
                intervals = self.pAintervals
        else:
            raise ValueError('Incorrect "supply_type" value: "%s"!\nAllowed values: "0", "1", "2".' % supply_type)

        t = datetime.datetime.now()
        strt = t.strftime("%Y.%m.%d_%H.%M")

        log = strt + '\n'
        try:
            for start, stop in intervals:
                newURL = baseURL + 'price1=' + str(start) + '&price2=' + str(stop) + '&'

                # Ограничение кол-ва запросов в минуту (рандомная задержка в секундах):
                tsleep = random.randint(2, 5)
                # Обратная связь:
                print "\nDon't worry, I'm working..."
                message = 'Current request: Start price = %s, Stop price = %s. Request URL:\n%s\n' % \
                          (start, stop, newURL)
                message += 'Wait %s seconds...' % tsleep
                print message
                time.sleep(tsleep)
                message += '\n\n'
                log += message

                result = None
                for attempt in range(15):
                    try:
                        result = r.open(newURL)
                        break
                    except Exception:
                        log += ('== Failure to retrieve HTML == (' + str(start) + ' - ' + str(stop) + ')\n')
                        log += (exception_str() + '\n\n')
                        print 'Repeating request.Wait 5 seconds...'
                        time.sleep(5)

                if not result:
                    message = 'There is no answer...'
                    print message
                    message += '\n\n'
                    log += message
                    continue
                # Перекодирование в Юникод
                page = result.read().decode("cp1251")

                # Нормализация файла
                soup = BeautifulSoup((''.join(page)))
                page = ''.join(soup.prettify())

                # Запись в файл
                htmlpath = os.path.join(path, 'HTMLs',
                                        'BNp%s_%s-%s.html' % (numtype, str(start).zfill(5), str(stop).zfill(5)))
                open(htmlpath, 'w').write(page)
        except:
            log += 'Something going wrong...\n'
            exc = exception_str()
            log += exc + '\n'
            print exc
        tend = time.time()
        twork = tend - tstart
        print '_'*50 + '\n'
        print "Time ", twork
        log += '_'*50 + '\n'
        log += 'Time ' + str(twork / 60) + '\n'
        log += '-'*120 + '\n\n'

        logpath = os.path.join(path, 'downloadingLog.txt')
        open(logpath, 'a').write(log)

