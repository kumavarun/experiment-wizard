##--------------------------------------%%
##   Convert Experiment Wizard output   ##
##           to .ARFF for Weka          ##
##         Author: Jeroen Kools         ##
##              Feb 2011                ##
##--------------------------------------#/

def getstrings(column,text, separator):
    values = []
    for line in text[1:]:
        cell = line.split(separator)[column].strip()
        if not(cell in values):
            values.append(cell)
    valstr = " {"
    for v in values:
        valstr = valstr+v+","
    valstr = valstr.strip(",")
    valstr = valstr+"}"    
    return valstr 

def csv2arff(file, online, response):
    print 'csv2arff!'
    # do stuff with selected file
    f = open(file,'r')
    n = file.replace(".csv","")        # drop extension
    t = str(n).rsplit("\\",1)[1]       # drop directory part 
    o = n+".arff"                      # create new file name
    text = f.readlines()
    output = open(o,'w')
    separator =''
    
    arffrelation = t.replace(' ','_').replace('\'','')
    output.write("@RELATION "+arffrelation+"\n")
    output.write("\n")
   
    # deal with different csv dialects
    if text[1].count(",") > text[1].count(";"):   
        separator= ","
    else:           
        separator = ";"

    # validate file and identify type
    headers = text[0].split(separator)

    minwidth = 56+3 # nr of columns without subject/stimulus attributes
    
    # add possible extra attributes
    extras = 0
    column = 1
    if response:
        if (len(headers) > minwidth):   
            header = headers[column]
            while not header == 'Response':
                extras += 1                
                # collect all values of string attribute
                valstr = getstrings(column,text, separator)
                output.write("@ATTRIBUTE "+header.strip()+valstr+"\n")
                column = column+1
                header = headers[column]
    
        responses = getstrings(column, text, separator)
        output.write("@ATTRIBUTE Response"+responses+"\n")
        output.write("@ATTRIBUTE Response_time REAL\n")
    
    # list sensors
    sensors = ("AF3","F7","F3","FC5","T7","P7","O1","O2",\
               "P8","T8","FC6","F4","F8","AF4")
    wavebands =  ("alpha","beta","delta","theta")
    if online:
        for s in sensors:
            for w in wavebands:
                output.write("@ATTRIBUTE "+s+'-'+w+" REAL\n")

    output.write("\n@DATA\n")
    # read values and write them to .arff file
    
    for i in range(1,len(text)):
        line = text[i]
        vals = line.split(separator)
        output.write(vals[1])
        for v in vals[2:]:
            if v.strip() == '':
                break
            output.write(','+str(v))
        output.write("\n")
       
    # save to new file
    output.close()
