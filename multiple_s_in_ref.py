# -*- coding: utf-8 -*-
"""
DISCLAIMER
Prototype - tested only on a few records

Creates:
xml file for upload in correct mode 
Separate xml-file if a reference was split into more than limitsplit=5 pubnotes
Logfile

ToDo:
suppress identical pubnotes / report numbers
"""
import re
import codecs
from invenio.search_engine import perform_request_search, get_record, get_fieldvalues
from invenio.bibrecord import record_delete_fields, record_add_field
from invenio.bibrecord import record_xml_output

def addto(counter, key, value):
    if type(key) == str:
        pass
    else:
        if type(key) == int:
            key = '%s' % key
        elif len(key) == 1:
            key = key[0]
        else:
            key = 'NN'
    if key in counter:
        counter[key].append(value)
    else:
        counter[key] = [value, ]
    return


def parse_reference(subfield):
#    arxiv = ['ASTRO', 'HEP', 'NUCL', 'GR', 'MATH', 'PHYSICS', 'COND']
    reference = {'a':[], 'r':[], 's':[]}
    for code, value in subfield:
        if code == 'm':
            for subvalue in value.split(' / '):
                if subvalue.startswith('Additional pubnote: '):
                    addto(reference, 's', subvalue[20:])
                else:
                    addto(reference, code, value)
        else:
            addto(reference, code, value)
    return reference

        
def split_reference(reference):
    if len(reference['s']) < 2:
        return 0
    sf_a = {'NN':[]}
    sf_r = {'NN':[]}
    sf_s = {'NN':[]}
    sf_mults = {}
    for value in reference['s']:
        ref_recids = perform_request_search(p='fin j "%s"' % value)
        if len(ref_recids) < 2:
            addto(sf_s, ref_recids, value)
        else:
            addto(sf_mults, value, ref_recids) # key is the PBN, value is list of recids
    for value in reference['a']:
        ref_recids = perform_request_search(p=value)
        addto(sf_a, ref_recids, value)
    for value in reference['r']:
        value.strip()
        repno = value.split(' ')[0].lower()
        repno = repno.strip('arxiv:')
        ref_recids = perform_request_search(p='reportnumber:%s' % repno)
        addto(sf_r, ref_recids, value)
    # see if the multiple PBNs belong to a single one
    for pbn, ref_recids in sf_mults.items():
        for ref_recid in ref_recids[0]:
            if ref_recid in sf_s.keys(): 
                sf_s[ref_recid].append(pbn)
                break
        else:
            sf_s[ref_recids[0][0]] = pbn            
        
    pbns = set(sf_a.keys() + sf_r.keys() + sf_s.keys())
    pbns.discard('NN')
    if not pbns:
        pbns = []
    else:
        pbns = list(pbns)
    # pbns: list of cited records in INSPIRE
    # sf_s['NN']: list of unresolved citations
    if len(pbns) + len(sf_s['NN']) > 1:            
        fields = []
        for ref_recid in pbns:
            subfields = []
            if ref_recid in sf_a:
                for value in sf_a[ref_recid]:
                    subfields.append(('a', value))
            if ref_recid in sf_r:
                for value in sf_r[ref_recid]:
                    subfields.append(('r', value))
            if ref_recid in sf_s:
                for value in sf_s[ref_recid]:
                    subfields.append(('s', value))
                years = get_fieldvalues(ref_recid, '773__y')
                if years:
                    subfields.append(('y', years[0]))
            if subfields:
                fields.append(subfields)
        subfields = []
        for value in sf_a['NN']:
            subfields.append(('a', value))
        for value in sf_r['NN']:
            subfields.append(('r', value))
        for value in sf_s['NN']:
            subfields.append(('s', value))
        if subfields:
            fields.append(subfields)
        if len(fields) == 1:
            # don't bother with it now
            return 0
        else:    
            return fields
    else:
        # don't bother with it now
        return 0

def main():
    from invenio.search_engine import get_collection_reclist
    tag = '999'
    limitsplit = 5  # write records with many PBNs in one reference to separate file
    recids = [1601941, 1783227, 1783287]
    # recids = get_collection_reclist("HEP")
    
    comment = 'Split reference'
    if len(recids) == 1:
        filename = 'multiple_s.%s' % recids[0]
    else:
        filename = 'multiple_s.out' 
    print 'Processing %s records - write to %s.*' % (len(recids), filename)
    
    xmlfile = codecs.EncodedFile(codecs.open('%s.correct' % filename, mode='wb'),'utf8')
    xmlmanyfile = codecs.EncodedFile(codecs.open('%s.many.correct' % filename, mode='wb'),'utf8')
    logfile = codecs.EncodedFile(codecs.open('%s.log' % filename, mode='wb'),'utf8')
    logfile.write('  Original reference\n= Common rest\n+ Split references\n')
    stats = {}
    nrec = 0
    for recid in recids:
        nrec += 1
        record = get_record(recid)
        update = False
        maxsplit = 0
        record_logtext = '\n%s ===========================\n' % recid
        for field in record_delete_fields(record, tag):
#            print '===================='
#            print '     ', field[0]
            reference = split_reference(parse_reference(field[0]))
            if not reference:
                record_add_field(record, tag, ind1=field[1], ind2=field[2], subfields=field[0])
            else:
                logtext = '\n  %s\n' % field[0]
                nsplit = 0
                rest = []
                years = []
                for code, value in field[0]:
                    if code in ['a', 'r', 's', '0']:
                        pass
                    elif code == '9' and value.upper() == 'CURATOR':
                        pass
                    elif code == 'y':
                        years.append(('y', value))
                    elif code == 'm':  
                        subvalues = []
                        for subvalue in value.split(' / '):
                            # get rid of the Additional pubnotes
                            if not subvalue.startswith('Additional pubnote: '):
                                subvalues.append(subvalue)
                        if subvalues:
                            rest.append(('m',' / '.join(subvalues)))
                    else:
                        rest.append((code, value))
                logtext += '= %s\n' % (rest + years, )
                for split_fields in reference:
                    if not split_fields:
                        continue
                    nsplit += 1
                    split_field_codes = []
                    need_year = True
                    for code, value in split_fields:
                        split_field_codes.append(code)
                        if code == 'y':
                            need_year = False
                    logtext += '+ %s \n' % split_fields
                    split_fields += rest
                    if need_year:
                        split_fields += years
                    split_fields.append(('m', comment))
#                    print '+ ', split_fields
                    record_add_field(record, tag, ind1=field[1], ind2=field[2], subfields=split_fields)
                update = True
                record_logtext += logtext
                if nsplit in stats:
                    stats[nsplit] += 1
                else:
                    stats[nsplit] = 1
                if nsplit > maxsplit:
                    maxsplit = nsplit
        if nrec % 100 == 0:
            print 'Here I am:', nrec, recid, stats
        if update:
            if maxsplit > limitsplit:
                outfile = xmlmanyfile
            else:
                outfile = xmlfile
            outfile.write(record_xml_output(record, ['001', '005', tag]))
            outfile.write('\n')
            logfile.write(record_logtext)
    print 'Done with %s records: %s' % (nrec, stats)
    logfile.write('\n\nDone with %s records: %s' % (nrec, stats))
    xmlfile.close()
    xmlmanyfile.close()
    logfile.close()

if __name__ == '__main__':
    main()                                                                      