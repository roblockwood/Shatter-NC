
/* OBJECT ID's */
var OBJ_APPLICATION_ID	= "0";
var OBJ_SERVICE_ID		= "1";
var OBJ_RESPONSE_CODE	= "2";
var OBJ_DATA			= "3";

/* Application Id enums */
var APP_ID_HMI					= 1;
var APP_ID_USERMANAGER			= 2;
var APP_ID_REPORTMANAGER		= 3;
var APP_ID_BACKUP				= 4;
var APP_ID_RESTORE				= 5;
var APP_ID_SW_UPDATE			= 6;
var APP_ID_TXT_MANAGER			= 7;
var APP_ID_SESSION_MANAGEMENT	= 8;

var APP_ID_DATARECORDER = "datarecorder";	//LH
var APP_ID_CREATE_USER = "createUser";		//LF

/* Service Id enums */
var SER_ID_HMI_GET_HMI_MENU		= 1;
var SER_ID_HMI_GET_HMI_OBJECTS	= 2;
var SER_ID_HMI_SET_HMI_OBJECT	= 3;
var SER_ID_HMI_GET_LED_STATUS	= 4;
var SER_ID_HMI_SET_KEY_STATUS	= 5;
var SER_ID_HMI_GET_LANGUAGES    = 6;
var SER_ID_HMI_GET_COMP_INFO    = 7;
var SER_ID_HMI_SET_LANGUAGE     = 8; 
var SER_ID_GET_USER_OBJECTS		= 1;
var SER_ID_SET_USER_OBJECT		= 2;
var SER_ID_DEL_USER_OBJECT		= 3;
var SER_ID_MOD_USER_OBJECT		= 4;
var SER_ID_GET_REPORT_OBJECTS	= 1;
var SER_ID_ACK_REPORT_OBJECT	= 2;
var SER_ID_BACKUP_PACKAGE		= 1;
var SER_ID_LOGOUT				= 1;
var SER_ID_LOGIN_READ_WRITE		= 2;
var SER_ID_SET_UNIT_SETTINGS	= 3;
var SER_ID_GET_EVENTS			= 4;
var SER_ID_DOWNGRADE_R_ACCESS   = 5;
var SER_ID_GET_TEXTS			= 1;
var SER_ID_UPDATE_SW            = 1;

var SER_ID_GET_TIMESTAMP	= 1;	//LH: 5 Service IDs
var SER_ID_GET_LAST_HOUR	= 2;
var SER_ID_GET_DATA			= 3;
var SER_ID_GET_CURRENT_DATA	= 4;
var SER_ID_IS_SFC			= 5;
var SER_ID_IS_WATERCOOLED	= 6;
var SER_ID_tMMethod = 7;
var SER_ID_T3_USE = 8;

var SER_ID_GET_IO_DATA			= 10;
var SER_ID_DR_IS_LONGTERM = 11;
var SER_ID_GET_START_OF_RECORDING = 12;
var SER_ID_DOWNLOAD_HOUR = 13;
var SER_ID_DOWNLOAD_INTERVAL = 14;
var SER_ID_GET_DR_COPY_STATUS_REQUEST = 15;
var SER_ID_VET_USE = 16;

var SER_ID_UPLOAD_REGFILE 	= 1;	//LF

/* Response codes */
var RESP_SUCCESS					= 0;
var RESP_GEN_FAIL					= 1;
var RESP_INCORRECT_JSON_FORMAT		= 2;
var RESP_SERVICE_ID_NOT_SUPPORTED	= 3;
var RESP_APP_ID_NOT_SUPPORTED		= 4;
var RESP_APP_LOGOUT					= 5;
var RESP_NOT_VALID					= 999;	/* used internally */

/* public variables */
var CallBackFunction_Logout = null;
var CallBackFunction_GetTexts = null;
var CallBackFunction_GetMessageEvents = null;
var CallBackFunction_GetHmiMenuStructure = null;
var CallBackFunction_GetHMIObjects = null;
var CallBackFunction_GetHmiLedStatus = null;
var CallBackFunction_SetHmiKeyStatus = null;
var CallBackFunction_GetReportObjects = null;
var CallBackFunction_AcknowledgeReportObject = null;
var CallBackFunction_GetUserObjects = null;
var CallBackFunction_SetUserObjects = null;
var CallBackFunction_DelUserObjects = null;
var CallBackFunction_ModUserObjects = null;
var CallBackFunction_LoginReadWrite = null;
var CallBackFunction_DownGradeToReadAccess = null;
var CallBackFunction_GetLanguages = null;
var CallBackFunction_SetLanguage = null;
var CallBackFunction_BackupPackage = null;
var CallBackFunction_SoftwareUpdate = null;
var CallBackFunction_GetCompressorInfo = null;

var CallBackFunction_GetTimestamp = null;	//LH: 5 Zeilen
var CallBackFunction_GetLastHour = null;
var CallBackFunction_GetData = null;
var CallBackFunction_GetCurrentData = null;
var CallBackFunction_IsSFC = null;
var CallBackFunction_DatarecorderError = null;
var CallBackFunction_IsWatercooled = null;
var CallBackFunction_tMMethod = null;
var CallBackFunction_t3Use = null;
var CallBackFunction_VETUse = null;

var CallBackFunction_GetIOData = null;

var CallBackFunction_UploadRegFile = null;	//LF

var TextIdBuffer = new Array();

//LF: IO-Display
function JSON_GetIOData(CallBackFunction)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_DATARECORDER,
			1:SER_ID_GET_IO_DATA,
			2:{}
		};
	   	CallBackFunction_GetIOData = CallBackFunction;	/* save the callbackfunction */
		JSONString = JSON.stringify(JSRequest);	/* parse the JS object to a JSON string  */
		SendJSONRequest(JSON_CallBack_GetIOData, JSONString, JSRequest[0], JSRequest[1]);	/* send JSON string */
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_GetIOData()!!!');
	}
}
function JSON_CallBack_GetIOData(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		if (JSResponse[0] == APP_ID_DATARECORDER)
		{
			if ((JSResponse[1] == SER_ID_GET_IO_DATA))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		//COM_CreatePopUpPromptBox('JSResponse[0] = ' + JSResponse[0] + ' JSResponse[1] = ' + JSResponse[1] + ' JSResponse[2] = ' + RetVal);
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			CallBackFunction_GetIOData(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_GetIOData()!!!');
	}
}
//LF: Upload Registration File
function JSON_UploadRegFile(CallBackFunction, data)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_CREATE_USER,
			1:SER_ID_UPLOAD_REGFILE,
			2:{"data": data}
		};
	
		/* save the callbackfunction */
	   	CallBackFunction_UploadRegFile = CallBackFunction;
	
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_UploadRegFile, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_UploadRegFile()!!!');
	}
}
function JSON_CallBack_UploadRegFile(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_CREATE_USER)
		{
			if ((JSResponse[1] == SER_ID_UPLOAD_REGFILE))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		//COM_CreatePopUpPromptBox('JSResponse[0] = ' + JSResponse[0] + ' JSResponse[1] = ' + JSResponse[1] + ' JSResponse[2] = ' + RetVal);
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			CallBackFunction_UploadRegFile(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_UploadRegFile()!!!');
	}
}

//LH: Graphs
function JSON_GetTimestamp(CallBackFunction)
{
	//COM_CreatePopUpPromptBox('In JSON_GetTimestamp.');
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_DATARECORDER,
			1:SER_ID_GET_TIMESTAMP,
			2:{}
		};
	
		/* save the callbackfunction */
	   	CallBackFunction_GetTimestamp = CallBackFunction;
	
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_GetTimestamp, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_GetTimestamp()!!!');
	}
}

function JSON_CallBack_GetTimestamp(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_DATARECORDER)
		{
			if ((JSResponse[1] == SER_ID_GET_TIMESTAMP))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		//COM_CreatePopUpPromptBox('JSResponse[0] = ' + JSResponse[0] + ' JSResponse[1] = ' + JSResponse[1] + ' JSResponse[2] = ' + RetVal);
		if (RetVal != RESP_SUCCESS) 
		{
			CallBackFunction_DatarecorderError();
			//COM_CreatePopUpPromptBox('RetVal ist nicht okay!');
			//COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			CallBackFunction_GetTimestamp(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_GetTimestamp()!!!');
	}
}

function JSON_GetLastHour(CallBackFunction, signal)
{
	var JSONString;
	try 
	{
		var JSRequest = 
		{
			0:APP_ID_DATARECORDER,
			1:SER_ID_GET_LAST_HOUR,
			2:{"signal1":signal}
		};
		CallBackFunction_GetLastHour = CallBackFunction;
		JSONString = JSON.stringify(JSRequest);
		SendJSONRequest(JSON_CallBack_GetLastHour, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_GetLastHour()!!!');
	}
}

function JSON_CallBack_GetLastHour(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		JSResponse = JSON.parse(JSONString);
		if (JSResponse[0] == APP_ID_DATARECORDER)
		{
			if ((JSResponse[1] == SER_ID_GET_LAST_HOUR))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		//COM_CreatePopUpPromptBox('JSResponse[0] = ' + JSResponse[0] + ' JSResponse[1] = ' + JSResponse[1] + ' JSResponse[2] = ' + RetVal);
		if (RetVal != RESP_SUCCESS) 
		{
			CallBackFunction_DatarecorderError();
			//COM_CreatePopUpPromptBox('RetVal ist nicht okay!');
			//COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			CallBackFunction_GetLastHour(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_GetLastHour()!!!');
	}
}

function JSON_GetData(CallBackFunction, timestamp, num, signal)
{
	var JSONString;
	try 
	{
		var JSRequest = 
		{
			0:APP_ID_DATARECORDER,
			1:SER_ID_GET_DATA,
			2:{"timestamp":timestamp,"num":num,"signal1":signal}
		};
		CallBackFunction_GetData = CallBackFunction;
		JSONString = JSON.stringify(JSRequest);
		SendJSONRequest(JSON_CallBack_GetData, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_GetData()!!!');
	}
}

var countTest = 0;
function JSON_CallBack_GetData(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		JSResponse = JSON.parse(JSONString);
		if (JSResponse[0] == APP_ID_DATARECORDER)
		{
			if ((JSResponse[1] == SER_ID_GET_DATA))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		//COM_CreatePopUpPromptBox('JSResponse[0] = ' + JSResponse[0] + ' JSResponse[1] = ' + JSResponse[1] + ' JSResponse[2] = ' + RetVal);
		countTest++;
		if (RetVal != RESP_SUCCESS) 
		{
			//COM_CreatePopUpPromptBox('RetVal ist nicht okay!');
			//COM_CreatePopUpPromptBox(RetVal, ErrorCode);
			CallBackFunction_DatarecorderError();
		}
		else
		{
			CallBackFunction_GetData(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_GetData()!!!');
		alert(e.message);
	}
}

function JSON_GetCurrentData(CallBackFunction, timestamp, signal)
{
	var JSONString;
	try 
	{
		var JSRequest = 
		{
			0:APP_ID_DATARECORDER,
			1:SER_ID_GET_CURRENT_DATA,
			2:{"timestamp":timestamp, "signal1":signal}
		};
		CallBackFunction_GetCurrentData = CallBackFunction;
		JSONString = JSON.stringify(JSRequest);
		SendJSONRequest(JSON_CallBack_GetCurrentData, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_GetCurrentCata()!!!');
	}
}

function JSON_CallBack_GetCurrentData(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		JSResponse = JSON.parse(JSONString);
		if (JSResponse[0] == APP_ID_DATARECORDER)
		{
			if ((JSResponse[1] == SER_ID_GET_CURRENT_DATA))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		//COM_CreatePopUpPromptBox('JSResponse[0] = ' + JSResponse[0] + ' JSResponse[1] = ' + JSResponse[1] + ' JSResponse[2] = ' + RetVal);
		if (RetVal != RESP_SUCCESS) 
		{
			//COM_CreatePopUpPromptBox('RetVal ist nicht okay!');
			//COM_CreatePopUpPromptBox(RetVal, ErrorCode);
			CallBackFunction_DatarecorderError();
		}
		else
		{
			CallBackFunction_GetCurrentData(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_GetCurrentData()!!!');
	}
}

function JSON_IsSFC(CallBackFunction, CallBackErrorFunction)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_DATARECORDER,
			1:SER_ID_IS_SFC,
			2:{}
		};
	
		/* save the callbackfunction */
	   	CallBackFunction_IsSFC = CallBackFunction;
	   	CallBackFunction_DatarecorderError = CallBackErrorFunction;
	
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_IsSFC, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_IsSFC()!!!');
	}
}

function JSON_CallBack_IsSFC(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		if (JSResponse[0] == APP_ID_DATARECORDER)
		{
			if ((JSResponse[1] == SER_ID_IS_SFC))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		if (RetVal != RESP_SUCCESS)
		{
			CallBackFunction_DatarecorderError();
		}
		else
		{
			CallBackFunction_IsSFC(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_IsSFC()!!!');
	}
}

function JSON_tMMethod(CallBackFunction, CallBackErrorFunction)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_DATARECORDER,
			1:SER_ID_tMMethod,
			2:{}
		};
	
		/* save the callbackfunction */
	   	CallBackFunction_tMMethod = CallBackFunction;
	   	CallBackFunction_DatarecorderError = CallBackErrorFunction;
	
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_tMMethod, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_tMMethod()!!!');
	}
}

function JSON_CallBack_tMMethod(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		if (JSResponse[0] == APP_ID_DATARECORDER)
		{
			if ((JSResponse[1] == SER_ID_tMMethod))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		if (RetVal != RESP_SUCCESS)
		{
			CallBackFunction_DatarecorderError();
		}
		else
		{
			CallBackFunction_tMMethod(JSResponse[3]);     
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_tMMethod()!!!');
	}
}

function JSON_t3Use(CallBackFunction, CallBackErrorFunction)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_DATARECORDER,
			1:SER_ID_T3_USE,
			2:{}
		};
	
		/* save the callbackfunction */
	   	CallBackFunction_t3Use = CallBackFunction;
	   	CallBackFunction_DatarecorderError = CallBackErrorFunction;
	
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_t3Use, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_t3Use()!!!');
	}
}

function JSON_CallBack_t3Use(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		if (JSResponse[0] == APP_ID_DATARECORDER)
		{
			if ((JSResponse[1] == SER_ID_T3_USE))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		if (RetVal != RESP_SUCCESS)
		{
			CallBackFunction_DatarecorderError();
		}
		else
		{
			CallBackFunction_t3Use(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_t3Use()!!!');
	}
}

function JSON_IsWatercooled(CallBackFunction)
{
	var JSONString;
	try 
	{
		var JSRequest = 
		{
			0:APP_ID_DATARECORDER,
			1:SER_ID_IS_WATERCOOLED,
			2:{}
		};
	   	CallBackFunction_IsWatercooled = CallBackFunction;
		JSONString = JSON.stringify(JSRequest);
		SendJSONRequest(JSON_CallBack_IsWatercooled, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_IsWatercooled()');
	}
}
function JSON_CallBack_IsWatercooled(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_DATARECORDER)
		{
			if ((JSResponse[1] == SER_ID_IS_WATERCOOLED))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		if (RetVal != RESP_SUCCESS)
		{
			CallBackFunction_DatarecorderError();
		}
		else
		{
			CallBackFunction_IsWatercooled(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_IsWatercooled()!!!');
	}
}

function JSON_VETUse(CallBackFunction, CallBackErrorFunction) {
  var JSONString;
  try {
    /* create the JS object request  */
    var JSRequest =
		{
		  0: APP_ID_DATARECORDER,
		  1: SER_ID_VET_USE,
		  2: {}
		};

    /* save the callbackfunction */
    CallBackFunction_VETUse = CallBackFunction;
    CallBackFunction_DatarecorderError = CallBackErrorFunction;

    /* parse the JS object to a JSON string  */
    JSONString = JSON.stringify(JSRequest);

    /* send JSON string */
    SendJSONRequest(JSON_CallBack_VETUse, JSONString, JSRequest[0], JSRequest[1]);
  }
  catch (e) {
    COM_CreatePopUpPromptBox('error in JSON_VETUse()!!!');
  }
}

function JSON_CallBack_VETUse(JSONString) {
  var JSResponse;
  var RetVal = null;
  var ErrorCode = RESP_NOT_VALID;
  try {
    /* parse the received JSON string to a JS object */
    JSResponse = JSON.parse(JSONString);

    if (JSResponse[0] == APP_ID_DATARECORDER) {
      if ((JSResponse[1] == SER_ID_VET_USE)) {
        RetVal = JSResponse[2];
        ErrorCode = null;
      }
    }
    if (RetVal != RESP_SUCCESS) {
      CallBackFunction_DatarecorderError();
    }
    else {
      CallBackFunction_VETUse(JSResponse[3]);
    }
  }
  catch (e) {
    COM_CreatePopUpPromptBox('error in JSON_CallBack_IsWatercooled()!!!');
  }
}

//Ende LH

function JSON_DR_IsLongterm(CallBackFunction)
{
	var JSONString;
	try 
		{ 		
        /* create the JS object request  */
        var JSRequest = 
        {
            0:APP_ID_DATARECORDER,
            1:SER_ID_DR_IS_LONGTERM,
						2:{}
        };
        
        /* save the callbackfunction */
        CallBackFunction_DR_IsLongterm = CallBackFunction;
        
        /* parse the JS object to a JSON string  */
        JSONString = JSON.stringify(JSRequest);

        /* send JSON string */
        SendJSONRequest(JSON_CallBack_DR_IsLongterm, JSONString, JSRequest[0], JSRequest[1]);
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in DR_IsLongterm()!!!');
    }
}

function JSON_CallBack_DR_IsLongterm(JSONString)
{
    var JSResponse;
    var RetVal = null;
    var ErrorCode = RESP_NOT_VALID;
    try 
    {
        /* parse the received JSON string to a JS object */
        JSResponse = JSON.parse(JSONString);
        
        if (JSResponse[0] == APP_ID_DATARECORDER)
        {
            if ((JSResponse[1] == SER_ID_DR_IS_LONGTERM))
            {
                RetVal = JSResponse[2];
                ErrorCode = null;
            }
        }
        
        if (RetVal != RESP_SUCCESS) 
        {
            COM_CreatePopUpPromptBox(RetVal, ErrorCode);
        }
        else
        {
            /* call the callback function */
            CallBackFunction_DR_IsLongterm(JSResponse[3]);
        }
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_CallBack_DR_IsLongterm()!!!');
    }
}
function JSON_GET_START_OF_RECORDING(CallBackFunction)
{
	var JSONString;
	try 
		{ 		
        /* create the JS object request  */
        var JSRequest = 
        {
            0:APP_ID_DATARECORDER,
            1:SER_ID_GET_START_OF_RECORDING,
						2:{}
        };
        
        /* save the callbackfunction */
        CallBackFunction_GET_START_OF_RECORDING = CallBackFunction;
        
        /* parse the JS object to a JSON string  */
        JSONString = JSON.stringify(JSRequest);

        /* send JSON string */
        SendJSONRequest(JSON_CallBack_GET_START_OF_RECORDING, JSONString, JSRequest[0], JSRequest[1]);
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in GET_START_OF_ RECORDING()!!!');
    }
}

function JSON_CallBack_GET_START_OF_RECORDING(JSONString)
{
    var JSResponse;
    var RetVal = null;
    var ErrorCode = RESP_NOT_VALID;
    try 
    {
        /* parse the received JSON string to a JS object */
        JSResponse = JSON.parse(JSONString);
        
        if (JSResponse[0] == APP_ID_DATARECORDER)
        {
            if ((JSResponse[1] == SER_ID_GET_START_OF_RECORDING))
            {
                RetVal = JSResponse[2];
                ErrorCode = null;
            }
        }
        
        if (RetVal != RESP_SUCCESS) 
        {
            COM_CreatePopUpPromptBox(RetVal, ErrorCode);
        }
        else
        {
            /* call the callback function */
            CallBackFunction_GET_START_OF_RECORDING(JSResponse[3]);
        }
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_GET_START_OF_RECORDING()!!!');
    }
}
function JSON_DOWNLOAD_HOUR(CallBackFunction, Timestamp)
{
	var JSONString;
	try 
		{ 		
        /* create the JS object request  */
        var JSRequest = 
        {
            0:APP_ID_DATARECORDER,
            1:SER_ID_DOWNLOAD_HOUR,
						2:{"Timestamp" : Timestamp}
        };
        
        /* save the callbackfunction */
        CallBackFunction_DOWNLOAD_HOUR = CallBackFunction;
        
        /* parse the JS object to a JSON string  */
        JSONString = JSON.stringify(JSRequest);

        /* send JSON string */
        SendJSONRequest(JSON_CallBack_DOWNLOAD_HOUR, JSONString, JSRequest[0], JSRequest[1]);
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_DOWNLOAD_HOUR()!!!');
    }
}

function JSON_CallBack_DOWNLOAD_HOUR(JSONString)
{
    var JSResponse;
    var RetVal = null;
    var ErrorCode = RESP_NOT_VALID;
    try 
    {
        /* parse the received JSON string to a JS object */
        JSResponse = JSON.parse(JSONString);
        
        if (JSResponse[0] == APP_ID_DATARECORDER)
        {
            if ((JSResponse[1] == SER_ID_DOWNLOAD_HOUR))
            {
                RetVal = JSResponse[2];
                ErrorCode = null;
            }
        }
        
        if (RetVal != RESP_SUCCESS) 
        {
            COM_CreatePopUpPromptBox("File not found");
            CallBackFunction_DOWNLOAD_HOUR(null);
        }
        else
        {
            /* call the callback function */
            CallBackFunction_DOWNLOAD_HOUR(JSResponse[3]);
        }
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_DOWNLOAD_HOUR()!!!');
    }
}

function JSON_DOWNLOAD_INTERVAL(CallBackFunction, start, end)
{
	var JSONString;
	try 
		{ 		
        /* create the JS object request  */
        var JSRequest = 
        {
            0:APP_ID_DATARECORDER,
            1:SER_ID_DOWNLOAD_INTERVAL,
						2:{"start" : start, "end" : end}
        };
        
        /* save the callbackfunction */
        CallBackFunction_DOWNLOAD_INTERVAL = CallBackFunction;
        
        /* parse the JS object to a JSON string  */
        JSONString = JSON.stringify(JSRequest);

        /* send JSON string */
        SendJSONRequest(JSON_CallBack_DOWNLOAD_INTERVAL, JSONString, JSRequest[0], JSRequest[1]);
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_DOWNLOAD_INTERVAL()!!!');
    }
}

function JSON_CallBack_DOWNLOAD_INTERVAL(JSONString)
{
    var JSResponse;
    var RetVal = null;
    var ErrorCode = RESP_NOT_VALID;
    try 
    {
        /* parse the received JSON string to a JS object */
        JSResponse = JSON.parse(JSONString);
        
        if (JSResponse[0] == APP_ID_DATARECORDER)
        {
            if ((JSResponse[1] == SER_ID_DOWNLOAD_INTERVAL))
            {
                RetVal = JSResponse[2];
                ErrorCode = null;
            }
        }
        
        if (RetVal != RESP_SUCCESS) 
        {
            COM_CreatePopUpPromptBox('File not found');
            CallBackFunction_DOWNLOAD_INTERVAL(null);
        }
        else
        {
            /* call the callback function */
            CallBackFunction_DOWNLOAD_INTERVAL(JSResponse[3]);
        }
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_DOWNLOAD_INTERVAL()!!!');
    }
}

function JSON_GET_DR_COPY_STATUS(CallBackFunction)
{
	var JSONString;
	try 
		{ 		
        /* create the JS object request  */
        var JSRequest = 
        {
            0:APP_ID_DATARECORDER,
            1:SER_ID_GET_DR_COPY_STATUS_REQUEST,
			2:{}
        };
        
        /* save the callbackfunction */
        CallBackFunction_GET_DR_COPY_STATUS = CallBackFunction;
        
        /* parse the JS object to a JSON string  */
        JSONString = JSON.stringify(JSRequest);

        /* send JSON string */
        SendJSONRequest(JSON_CallBack_GET_DR_COPY_STATUS, JSONString, JSRequest[0], JSRequest[1]);
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_GET_DR_COPY_STATUS()!!!');
    }
}

function JSON_CallBack_GET_DR_COPY_STATUS(JSONString)
{
    var JSResponse;
    var RetVal = null;
    var ErrorCode = RESP_NOT_VALID;
    try 
    {
        /* parse the received JSON string to a JS object */
        JSResponse = JSON.parse(JSONString);
        
        if (JSResponse[0] == APP_ID_DATARECORDER)
        {
            if ((JSResponse[1] == SER_ID_GET_DR_COPY_STATUS_REQUEST))
            {
                RetVal = JSResponse[2];
                ErrorCode = null;
            }
        }
        
        if (RetVal != RESP_SUCCESS) 
        {
            COM_CreatePopUpPromptBox(RetVal, ErrorCode);
        }
        else
        {
            /* call the callback function */
            CallBackFunction_GET_DR_COPY_STATUS(JSResponse[3]);
        }
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_DOWNLOAD_INTERVAL()!!!');
    }
}


function JSON_Logout(CallBackFunction)
{
	var JSONString;
	
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_SESSION_MANAGEMENT,
			1:SER_ID_LOGOUT
		};
	
	   /* save the callbackfunction */
        CallBackFunction_Logout = CallBackFunction;
	
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_Logout, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_Logout()!!!');
	}
}

function JSON_CallBack_Logout(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_SESSION_MANAGEMENT)
		{
			if ((JSResponse[1] == SER_ID_LOGOUT))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			CallBackFunction_Logout();
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_Logout()!!!');
	}
}

function JSON_GetTexts(CallBackFunction, TextIdArray)
{
	var JSONString;
	var TextIdArrayNotCached = new Array();
	
	TextIdBuffer = TextIdArray; //remember the requested text id's
	
	for (Counter = 0; Counter < TextIdArray.length; Counter++)
	{	
		try
		{
			Text = localStorage.getItem('TEXT_ID_' + TextIdArray[Counter]);			
			if (Text == null)
			{
				TextIdArrayNotCached.push(TextIdArray[Counter]);	
			}
		}
		catch(e)
		{
			TextIdArrayNotCached.push(TextIdArray[Counter]);
		}
	}
	
	if (TextIdArrayNotCached.length > 0)
	{
		try 
		{	
			/* create the JS object request  */
			var JSRequest = 
			{
				0:APP_ID_TXT_MANAGER,
				1:SER_ID_GET_TEXTS,
				2:{0:TextIdArrayNotCached}
			};
		
			/* save the callbackfunction */
			CallBackFunction_GetTexts = CallBackFunction;
			
			/* parse the JS object to a JSON string  */
			JSONString = JSON.stringify(JSRequest);
	
			/* send JSON string */
			SendJSONRequest(JSON_CallBack_GetTexts, JSONString, JSRequest[0], JSRequest[1]);
		} 
		catch (e) 
		{
			COM_CreatePopUpPromptBox('error in JSON_GetTexts()2!!!');
		}
	}
	else
	{
		/* all ids are in the cache */
		CallBackFunction_GetTexts = CallBackFunction;		
		JSON_CallBack_GetTextsCached();
	}
}

function JSON_CallBack_GetTexts(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	var Counter = 0;
	var NrCachedItems = 0;
		
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_TXT_MANAGER)
		{
			if ((JSResponse[1] == SER_ID_GET_TEXTS))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			TextObjects = JSResponse[3];
			if (TextObjects != null)
			{	while (TextObjects[Counter] != null)
				{				
					try
					{		
						localStorage.setItem('TEXT_ID_' + TextObjects[Counter].TextId, TextObjects[Counter].Text);
						NrCachedItems++;
					} 
					catch (e) 
					{
						COM_CreatePopUpPromptBox('Failed to write Text ID to local storage!!!');
					}					
					Counter++;
				}
			}
			
			if(NrCachedItems > 0)
			{
				JSON_CallBack_GetTextsCached();				
			}
			else
			{
				/* call the callback function */
//				CallBackFunction_GetTexts(JSResponse[3]);
			}
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_GetTexts()!!!');
	}
	
}

function JSON_CallBack_GetTextsCached()
{
	var TextBuffer2 = new Array();
	var Counter;
	
	try
	{	
		for (Counter =0; Counter < TextIdBuffer.length; Counter++)
		{						
			var TextBufferStructure =
			{
				TextId : null,
				Text: null
			};
		
			TextBufferStructure.TextId = TextIdBuffer[Counter];
			TextBufferStructure.Text = TextIdBuffer[Counter];
						
			try
			{
				Text = localStorage.getItem('TEXT_ID_' + TextIdBuffer[Counter]);				
				if (Text != null)
				{
					TextBufferStructure.Text = Text;
//					COM_CreatePopUpPromptBox(TextBufferStructure.Text);					
				}
			}
			catch(e)
			{
				/* Continue */
				COM_CreatePopUpPromptBox('JSON_CallBack_GetTextsCached()2!!!');
			}	
			TextBuffer2.push(TextBufferStructure);	
								
		}
	}
	catch (e)
	{
		COM_CreatePopUpPromptBox('JSON_CallBack_GetTextsCached()!!!');
	}	
	
	
//	for (Counter =0; Counter < TextBuffer2.length; Counter++)
//	{	
//		COM_CreatePopUpPromptBox(TextBuffer2[Counter].TextId);
//	}
		
	CallBackFunction_GetTexts(TextBuffer2);	
}

function JSON_GetMessageEvents(CallBackFunction)
{
	var JSONString;
	
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_SESSION_MANAGEMENT,
			1:SER_ID_GET_EVENTS
		};
		
		/* save the callbackfunction */
		CallBackFunction_GetMessageEvents = CallBackFunction;
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_GetMessageEvents, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_GetMessageEvents()!!!');
	}
}

function JSON_CallBack_GetMessageEvents(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_SESSION_MANAGEMENT)
		{
			if ((JSResponse[1] == SER_ID_GET_EVENTS))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else 
		{
			/* call the function that prints the events to screen */
			CallBackFunction_GetMessageEvents(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_GetMessageEvents()!!!');
	}
}

function JSON_GetHmiMenuStructure(CallBackFunction)
{
	var JSONString;
	
	try
	{
		JSONString = localStorage.getItem("MENU_TREE");

		if (JSONString != null)
		{
			/* save the callbackfunction */
			CallBackFunction_GetHmiMenuStructure = CallBackFunction;			
			JSON_CallBack_GetHmiMenuStructure(JSONString);
			return;
		}
	}
	catch(e)
	{
		/* Continue */
	}
	
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_HMI,
			1:SER_ID_HMI_GET_HMI_MENU
		};
		
		/* save the callbackfunction */
		CallBackFunction_GetHmiMenuStructure = CallBackFunction;
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_GetHmiMenuStructure, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_GetHmiMenuStructure()!!!');
	}
}

function JSON_CallBack_GetHmiMenuStructure(JSONString)
{
	var JSResponse = null;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		try
		{	
			if (localStorage.getItem("MENU_TREE") == null) 
			{
				localStorage.setItem("MENU_TREE", JSONString);
			}
		} 
		catch (e) 
		{
			COM_CreatePopUpPromptBox('Failed to write menu tree to local storage!!!');
		}					
			
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_HMI)
		{
			if ((JSResponse[1] == SER_ID_HMI_GET_HMI_MENU))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			/* call the callback function */
			CallBackFunction_GetHmiMenuStructure(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_GetHmiMenuStructure()!!!');
	}
}

function JSON_GetHMIObjects(CallBackFunction, ObjectIdArray)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_HMI,
			1:SER_ID_HMI_GET_HMI_OBJECTS,
			2:{0:ObjectIdArray}
		};
		
		/* save the callbackfunction */
		CallBackFunction_GetHMIObjects = CallBackFunction;
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_GetHMIObjects, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_GetHMIObjects()!!!');
	}
}

function JSON_CallBack_GetHMIObjects(JSONString)
{
	var JSResponse = null;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_HMI)
		{
			if ((JSResponse[1] == SER_ID_HMI_GET_HMI_OBJECTS))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			/* call the callback function */
			CallBackFunction_GetHMIObjects(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_GetHMIObjects()!!!');
	}
}

function JSON_SetHMIObject(ObjectId)
{
    var JSONString;
    try 
    {
        /* create the JS object request  */
        var JSRequest = 
        {
            0:APP_ID_HMI,
            1:SER_ID_HMI_SET_HMI_OBJECT,
            2:{0:ObjectId}
        };
        
        /* parse the JS object to a JSON string  */
        JSONString = JSON.stringify(JSRequest);

        /* send JSON string */
        SendJSONRequest(JSON_CallBack_SetHMIObject, JSONString, JSRequest[0], JSRequest[1]);
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_SetHMIObject()!!!');
    }
}

function JSON_CallBack_SetHMIObject(JSONString)
{
    var JSResponse = null;
    var RetVal = null;
    var ErrorCode = RESP_NOT_VALID;
    try 
    {
        /* parse the received JSON string to a JS object */
        JSResponse = JSON.parse(JSONString);
        
        if (JSResponse[0] == APP_ID_HMI)
        {
            if ((JSResponse[1] == SER_ID_HMI_SET_HMI_OBJECT))
            {
                RetVal = JSResponse[2];
                ErrorCode = null;
            }
        }
        
        if (RetVal != RESP_SUCCESS) 
        {
            COM_CreatePopUpPromptBox(RetVal, ErrorCode);
        }
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_CallBack_SetHMIObject()!!!');
    }
}

function JSON_GetHmiLedStatus(CallBackFunction)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_HMI,
			1:SER_ID_HMI_GET_LED_STATUS
		};
		
		/* save the callbackfunction */
		CallBackFunction_GetHmiLedStatus = CallBackFunction;
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_GetHmiLedStatus, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_GetHmiLedStatus()!!!');
	}
}


function JSON_CallBack_GetHmiLedStatus(JSONString)
{
	var JSResponse = null;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_HMI)
		{
			if ((JSResponse[1] == SER_ID_HMI_GET_LED_STATUS))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			/* call the callback function */
			CallBackFunction_GetHmiLedStatus(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_GetHmiLedStatus()!!!');
	}
}

function JSON_SetHmiKeyStatus(CallBackFunction, KeyId, KeyState)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_HMI,
			1:SER_ID_HMI_SET_KEY_STATUS,
			2:{0:KeyId,1:KeyState}
		};
		
		/* save the callbackfunction */
		CallBackFunction_SetHmiKeyStatus = CallBackFunction;
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_SetHmiKeyStatus, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_SetHmiKeyStatus()!!!');
	}
}

function JSON_CallBack_SetHmiKeyStatus(JSONString)
{
	var JSResponse = null;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_HMI)
		{
			if ((JSResponse[1] == SER_ID_HMI_SET_KEY_STATUS))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			/* call the callback function */
			CallBackFunction_SetHmiKeyStatus(JSResponse[3][0],JSResponse[3][1]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_SetHmiKeyStatus()!!!');
	}
}

function JSON_GetReportObjects(CallBackFunction, ReportList, StartIndex, NrOfReports)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_REPORTMANAGER,
			1:SER_ID_GET_REPORT_OBJECTS,
			2:{0:ReportList, 1:StartIndex, 2:NrOfReports}
		};
		
		/* save the callbackfunction */
		CallBackFunction_GetReportObjects = CallBackFunction;
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_GetReportObjects, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		/* do nothing */
		COM_CreatePopUpPromptBox('error in JSON_GetReportObjects()!!!');
	}
}

function JSON_CallBack_GetReportObjects(JSONString)
{
	var JSResponse = null;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_REPORTMANAGER)
		{
			if ((JSResponse[1] == SER_ID_GET_REPORT_OBJECTS))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			/* call the function that prints the reports to screen */
			CallBackFunction_GetReportObjects(JSResponse);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_GetReportObjects()!!!');
	}
}

function JSON_AcknowledgeReportObject(CallBackFunction, ReportObject)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_REPORTMANAGER,
			1:SER_ID_ACK_REPORT_OBJECT,
			2:{0:ReportObject}
		};
		
		/* save the callbackfunction */
		CallBackFunction_AcknowledgeReportObject = CallBackFunction;
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_AcknowledgeReportObject, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		/* do nothing */
		COM_CreatePopUpPromptBox('error in JSON_AcknowledgeReportObject()!!!');
	}
}

function JSON_CallBack_AcknowledgeReportObject(JSONString)
{
	var JSResponse = null;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_REPORTMANAGER)
		{
			if ((JSResponse[1] == SER_ID_ACK_REPORT_OBJECT))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			/* call the callback function */
			CallBackFunction_AcknowledgeReportObject();
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_AcknowledgeReportObject()!!!');
	}
}

function JSON_GetUserObjects(CallBackFunction)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_USERMANAGER,
			1:SER_ID_GET_USER_OBJECTS
		};
		
		/* save the callbackfunction */
		CallBackFunction_GetUserObjects = CallBackFunction;
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_GetUserObjects, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		/* do nothing */
		COM_CreatePopUpPromptBox('error in JSON_GetUserObjects()!!!');
	}
}

function JSON_CallBack_GetUserObjects(JSONString)
{
	var JSResponse = null;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_USERMANAGER)
		{
			if ((JSResponse[1] == SER_ID_GET_USER_OBJECTS))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			/* call the function that prints the users to screen */
			CallBackFunction_GetUserObjects(JSResponse);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_GetUserObjects()!!!');
	}
}

function JSON_SetUserObject(CallBackFunction, UserObject)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_USERMANAGER,
			1:SER_ID_SET_USER_OBJECT,
			2: {0:UserObject}
		};
		
		/* save the callbackfunction */
		CallBackFunction_SetUserObjects = CallBackFunction;
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_SetUserObject, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		/* do nothing */
		COM_CreatePopUpPromptBox('error in JSON_SetUserObject()!!!');
	}
}

function JSON_CallBack_SetUserObject(JSONString)
{
	var JSResponse = null;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_USERMANAGER)
		{
			if ((JSResponse[1] == SER_ID_SET_USER_OBJECT))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			/* call the callback function */
			CallBackFunction_SetUserObjects();
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_SetUserObject()!!!');
	}
}

function JSON_DelUserObject(CallBackFunction, UserObject)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_USERMANAGER,
			1:SER_ID_DEL_USER_OBJECT,
			2: {0:UserObject}
		};
		
		/* save the callbackfunction */
		CallBackFunction_DelUserObjects = CallBackFunction;
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_DelUserObject, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		/* do nothing */
		COM_CreatePopUpPromptBox('error in JSON_DelUserObject()!!!');
	}
}

function JSON_CallBack_DelUserObject(JSONString)
{
	var JSResponse = null;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_USERMANAGER)
		{
			if ((JSResponse[1] == SER_ID_DEL_USER_OBJECT))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			/* call the callback function */
			CallBackFunction_DelUserObjects();
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_DelUserObject()!!!');
	}
}

function JSON_ModUserObject(CallBackFunction, OldUserObject, NewUserObject)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_USERMANAGER,
			1:SER_ID_MOD_USER_OBJECT,
			2: {0:OldUserObject,1:NewUserObject}
		};
		
		/* save the callbackfunction */
		CallBackFunction_ModUserObjects = CallBackFunction;
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_ModUserObject, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		/* do nothing */
		COM_CreatePopUpPromptBox('error in JSON_ModUserObject()!!!');
	}
}

function JSON_CallBack_ModUserObject(JSONString)
{
	var JSResponse = null;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_USERMANAGER)
		{
			if ((JSResponse[1] == SER_ID_MOD_USER_OBJECT))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			/* call the callback function */
			CallBackFunction_ModUserObjects();
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_ModUserObject()!!!');
	}
}

function JSON_LoginReadWrite(CallBackFunction, Username, LoginPhrase)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_SESSION_MANAGEMENT,
			1:SER_ID_LOGIN_READ_WRITE,
			2: {0:Username, 1:LoginPhrase}
		};
		
		/* save the callbackfunction */
		CallBackFunction_LoginReadWrite = CallBackFunction;
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_LoginReadWrite, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		/* do nothing */
		COM_CreatePopUpPromptBox('error in JSON_LoginReadWrite()!!!');
	}
}

function JSON_CallBack_LoginReadWrite(JSONString)
{
	var JSResponse = null;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		RetVal = JSResponse[2];
		
		if (JSResponse[0] == APP_ID_SESSION_MANAGEMENT)
		{
			if ((JSResponse[1] == SER_ID_LOGIN_READ_WRITE))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			/* call the callback function */
			CallBackFunction_LoginReadWrite();
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_LoginReadWrite()!!!');
	}
}

function JSON_DownGradeToReadAccess(CallBackFunction)
{
    var JSONString;
    try 
    {
        /* create the JS object request  */
        var JSRequest = 
        {
            0:APP_ID_SESSION_MANAGEMENT,
            1:SER_ID_DOWNGRADE_R_ACCESS
        };
        
        /* save the callbackfunction */
        CallBackFunction_DownGradeToReadAccess = CallBackFunction;
        
        /* parse the JS object to a JSON string  */
        JSONString = JSON.stringify(JSRequest);

        /* send JSON string */
        SendJSONRequest(CallBack_DownGradeToReadAccess, JSONString, JSRequest[0], JSRequest[1]);
    } 
    catch (e) 
    {
        /* do nothing */
        COM_CreatePopUpPromptBox('error in JSON_DownGradeToReadAccess()!!!');
    }
}

function CallBack_DownGradeToReadAccess(JSONString)
{
    var JSResponse = null;
    var RetVal = null;
    var ErrorCode = RESP_NOT_VALID;
    try 
    {
        /* parse the received JSON string to a JS object */
        JSResponse = JSON.parse(JSONString);
        
        RetVal = JSResponse[2];
        
        if (JSResponse[0] == APP_ID_SESSION_MANAGEMENT)
        {
            if ((JSResponse[1] == SER_ID_DOWNGRADE_R_ACCESS))
            {
                RetVal = JSResponse[2];
                ErrorCode = null;
            }
        }
        
        if (RetVal != RESP_SUCCESS) 
        {
            COM_CreatePopUpPromptBox(RetVal, ErrorCode);
        }
        else
        {
            /* call the callback function */
            CallBackFunction_DownGradeToReadAccess();
        }
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in CallBack_DownGradeToReadAccess()!!!');
    }
}

function JSON_SetUnitSettings(UnitSettingsObject)
{
	var JSONString;
	try 
	{
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_SESSION_MANAGEMENT,
			1:SER_ID_SET_UNIT_SETTINGS,
			2:UnitSettingsObject
		};
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_SetUnitSettings, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		/* do nothing */
		COM_CreatePopUpPromptBox('error in JSON_SetUnitSettings()!!!');
	}
}

function JSON_CallBack_SetUnitSettings(JSONString)
{
	var JSResponse = null;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		RetVal = JSResponse[2];
		
		if (JSResponse[0] == APP_ID_SESSION_MANAGEMENT)
		{
			if ((JSResponse[1] == SER_ID_SET_UNIT_SETTINGS))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_SetUnitSettings()!!!');
	}
}

function JSON_GetLanguages(CallBackFunction)
{
    var JSONString;
    try 
    {
        /* create the JS object request  */
        var JSRequest = 
        {
            0:APP_ID_HMI,
            1:SER_ID_HMI_GET_LANGUAGES
        };
        
		/* save the callbackfunction */
        CallBackFunction_GetLanguages = CallBackFunction;
		
        /* parse the JS object to a JSON string  */
        JSONString = JSON.stringify(JSRequest);

        /* send JSON string */
        SendJSONRequest(JSON_CallBack_GetLanguages, JSONString, JSRequest[0], JSRequest[1]);
    } 
    catch (e) 
    {
        /* do nothing */
        COM_CreatePopUpPromptBox('error in JSON_GetLanguages()!!!');
    }
}

function JSON_CallBack_GetLanguages(JSONString)
{
    var JSResponse = null;
    var RetVal = null;
    var ErrorCode = RESP_NOT_VALID;
    try 
    {
        /* parse the received JSON string to a JS object */
        JSResponse = JSON.parse(JSONString);
        
        RetVal = JSResponse[2];
        
        if (JSResponse[0] == APP_ID_HMI)
        {
            if ((JSResponse[1] == SER_ID_HMI_GET_LANGUAGES))
            {
                RetVal = JSResponse[2];
                ErrorCode = null;
            }
        }
        
        if (RetVal != RESP_SUCCESS) 
        {
            COM_CreatePopUpPromptBox(RetVal, ErrorCode);
        }
        else
        {
            /* call the callback function */
            CallBackFunction_GetLanguages(JSResponse[3]);
        }
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_CallBack_GetLanguages()!!!');
    }
}

function JSON_SetLanguage(CallBackFunction, CountryCode)
{
    var JSONString;
    try 
    {
        /* create the JS object request  */
        var JSRequest = 
        {
            0:APP_ID_HMI,
            1:SER_ID_HMI_SET_LANGUAGE,
            2:{0:CountryCode}
        };
        
		/* save the callbackfunction */
        CallBackFunction_SetLanguage = CallBackFunction;
		
        /* parse the JS object to a JSON string  */
        JSONString = JSON.stringify(JSRequest);

        /* send JSON string */
        SendJSONRequest(JSON_CallBack_SetLanguage, JSONString, JSRequest[0], JSRequest[1]);
    } 
    catch (e) 
    {
        /* do nothing */
        COM_CreatePopUpPromptBox('error in JSON_SetLanguage()!!!');
    }
}

function JSON_CallBack_SetLanguage(JSONString)
{
    var JSResponse = null;
    var RetVal = null;
    var ErrorCode = RESP_NOT_VALID;
    try 
    {
        /* parse the received JSON string to a JS object */
        JSResponse = JSON.parse(JSONString);
        
        RetVal = JSResponse[2];
        
        if (JSResponse[0] == APP_ID_HMI)
        {
            if ((JSResponse[1] == SER_ID_HMI_SET_LANGUAGE))
            {
                RetVal = JSResponse[2];
                ErrorCode = null;
            }
        }
        
        if (RetVal != RESP_SUCCESS) 
        {
            COM_CreatePopUpPromptBox(RetVal, ErrorCode);
        }
		else
		{
			 /* call the callback function */
            CallBackFunction_SetLanguage();
		}
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_CallBack_SetLanguage()!!!');
    }
}

function JSON_BackupPackage(CallBackFunction, PackageId)
{
	var JSONString;
	try 
	{	
		/* create the JS object request  */
		var JSRequest = 
		{
			0:APP_ID_BACKUP,
			1:SER_ID_BACKUP_PACKAGE,
			2:{0:PackageId}
		};
		
		/* save the callbackfunction */
		CallBackFunction_BackupPackage = CallBackFunction;
		
		/* parse the JS object to a JSON string  */
		JSONString = JSON.stringify(JSRequest);

		/* send JSON string */
		SendJSONRequest(JSON_CallBack_BackupPackage, JSONString, JSRequest[0], JSRequest[1]);
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_BackupPackage()!!!');
	}
}

function JSON_CallBack_BackupPackage(JSONString)
{
	var JSResponse;
	var RetVal = null;
	var ErrorCode = RESP_NOT_VALID;
	try 
	{
		/* parse the received JSON string to a JS object */
		JSResponse = JSON.parse(JSONString);
		
		if (JSResponse[0] == APP_ID_BACKUP)
		{
			if ((JSResponse[1] == SER_ID_BACKUP_PACKAGE))
			{
				RetVal = JSResponse[2];
				ErrorCode = null;
			}
		}
		
		if (RetVal != RESP_SUCCESS) 
		{
			COM_CreatePopUpPromptBox(RetVal, ErrorCode);
		}
		else
		{
			/* call the callback function */
			CallBackFunction_BackupPackage(JSResponse[3]);
		}
	} 
	catch (e) 
	{
		COM_CreatePopUpPromptBox('error in JSON_CallBack_BackupPackage()!!!');
	}
}

function JSON_SoftwareUpdate(CallBackFunction)
{
    var JSONString;
    try 
    {   
        /* create the JS object request  */
        var JSRequest = 
        {
            0:APP_ID_SW_UPDATE,
            1:SER_ID_UPDATE_SW
        };
        
        /* save the callbackfunction */
        CallBackFunction_SoftwareUpdate = CallBackFunction;
        
        /* parse the JS object to a JSON string  */
        JSONString = JSON.stringify(JSRequest);

        /* send JSON string */
        SendJSONRequest(JSON_CallBack_SoftwareUpdate, JSONString, JSRequest[0], JSRequest[1]);
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_SoftwareUpdate()!!!');
    }
}

function JSON_CallBack_SoftwareUpdate(JSONString)
{
    var JSResponse;
    var RetVal = null;
    var ErrorCode = RESP_NOT_VALID;
    try 
    {
        /* parse the received JSON string to a JS object */
        JSResponse = JSON.parse(JSONString);
        
        if (JSResponse[0] == APP_ID_SW_UPDATE)
        {
            if ((JSResponse[1] == SER_ID_UPDATE_SW))
            {
                RetVal = JSResponse[2];
                ErrorCode = null;
            }
        }
        
        if (RetVal != RESP_SUCCESS) 
        {
            COM_CreatePopUpPromptBox(RetVal, ErrorCode);
        }
        else
        {
            /* call the callback function */
            CallBackFunction_SoftwareUpdate();
        }
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_CallBack_SoftwareUpdate()!!!');
    }
}

function JSON_GetCompressorInfo(CallBackFunction, Cached)
{
    var JSONString;
      
	if (Cached == true)
	{
		try
		{
    		JSONString = sessionStorage.getItem("COMPRESSOR_INFO");
			if (JSONString != null)
			{
				/* save the callbackfunction */
				CallBackFunction_GetCompressorInfo = CallBackFunction;			
				JSON_CallBack_GetCompressorInfo(JSONString);
				return;
			}
		}
		catch(e)
		{
			/* Continue */
		}
	} 
		
    try 
    {   
        /* create the JS object request  */
        var JSRequest = 
        {
            0:APP_ID_HMI,
            1:SER_ID_HMI_GET_COMP_INFO
        };
        
        /* save the callbackfunction */
        CallBackFunction_GetCompressorInfo = CallBackFunction;
        
        /* parse the JS object to a JSON string  */
        JSONString = JSON.stringify(JSRequest);

        /* send JSON string */
        SendJSONRequest(JSON_CallBack_GetCompressorInfo, JSONString, JSRequest[0], JSRequest[1]);
        
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_GetCompressorInfo()!!!');
    }
}

function JSON_CallBack_GetCompressorInfo(JSONString)
{
    var JSResponse;
    var RetVal = null;
    var ErrorCode = RESP_NOT_VALID;            
  
    try 
    {
		try
		{								
			ComprInfo1= sessionStorage.getItem("COMPRESSOR_INFO");
			if ((ComprInfo1 == null) || (ComprInfo != JSONString))
			{
				sessionStorage.setItem("COMPRESSOR_INFO", JSONString);
			}
			
			ComprInfo1= sessionStorage.getItem("COMPRESSOR_INFO");
			ComprInfo2= localStorage.getItem("COMPRESSOR_INFO");
			if((ComprInfo2 == null) || (ComprInfo1 != ComprInfo2))
			{
				COM_ClearLocalStorage(REM_CACHE_ERASE_MENU_TREE); /* clear cached menu tree */			
				COM_ClearLocalStorage(REM_CACHE_ERASE_TEXTS); /* clear all cached text id's */
				localStorage.setItem("COMPRESSOR_INFO", ComprInfo1);
			}
		} 
		catch (e) 
		{
			/* continue */
		}    	

        /* parse the received JSON string to a JS object */
        JSResponse = JSON.parse(JSONString);
               
        if (JSResponse[0] == APP_ID_HMI)
        {
            if ((JSResponse[1] == SER_ID_HMI_GET_COMP_INFO))
            {
                RetVal = JSResponse[2];
                ErrorCode = null;
            }
        }       
        
        if (RetVal != RESP_SUCCESS) 
        {
            COM_CreatePopUpPromptBox(RetVal, ErrorCode);
        }
        else
        {

            /* call the callback function */
            CallBackFunction_GetCompressorInfo(JSResponse[3]);
        }
    } 
    catch (e) 
    {
        COM_CreatePopUpPromptBox('error in JSON_CallBack_GetCompressorInfo()!!!');
    }
}

