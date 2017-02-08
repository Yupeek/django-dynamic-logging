/**
 * Created by dbernard on 07/02/17.
 */


/**
 * load the json encoded data end addapt it to the form
 * in fact, it make the object of loggers (name, val) into a list of dict with name as a key
 * @param json the data encoded as a json string
 * @returns {{loggers: Array}} the data to pass to the form
 */
function load_form(json) {
  if (json === '') {
    json = '{}';
  }
  var data = JSON.parse(json),
    loggers = [],
    handlers = [];
  $.each(data.loggers || {}, function (loggername, logger) {
    logger.name = loggername;
    loggers.push(logger);
  });
  $.each(data.handlers || {}, function (handlername, handler) {
    handler.name = handlername;
    handlers.push(handler);
  });
  return {'loggers': loggers, 'handlers': handlers}
}

/**
 * dump the data from the form as a json encoded string
 * @param data
 * @returns {{loggers: Array}} the data of the form encoded
 */
function dump_form(data) {
  var loggers = {}, handlers = {}, lname;
  $.each(data.loggers, function (i, logger) {
    logger = $.extend(true, {}, logger);
    lname = logger.name;
    delete logger.name;
    loggers[lname] = logger;
  });
  $.each(data.handlers, function (i, handler) {
    handler = $.extend(true, {}, handler);
    lname = handler.name;
    delete handler.name;
    handlers[lname] = handler;
  });
  return JSON.stringify({'loggers': loggers, 'handlers': handlers});
}

function logging_widget(anchor, data, extra_select) {
  console.debug(anchor, data);
  var logger_conifg = {
      "loggers": [
        {"name": "django", "level": "1", "handlers": ["devnull"]},
        {"name": "django.db", "level": "3", "handlers": ["devnull"]}
      ]
    }, levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'],
    handlers = extra_select.handlers,
    filters = extra_select.filters,
    select_size = Math.max(handlers.length, filters.length),
    form_text = data.val(),
    global_data = load_form(form_text);


  //JSON.parse(data.val());
  // Manifest
  var manifest = {
    params:{remember:50, historyDelay:100},
    // Init function
    init: function ($form, runtime) {
      $form.html(this.MainHTML);
      this.Logger.LoggerHTML = this.LoggerHTML;
      this.Handler.HandlerHTML = this.HandlerHTML;
      $form.then(function () {
        $form.on('change', function () {
          data.val(dump_form($form.my("data")));
        })
      })
    },
    // Bindings
    ui: {
      "#loggers": {
        bind: "loggers",
        manifest: "Logger",
        list: '<tr></tr>'
      },
      "#handlers": {
        bind: "handlers",
        manifest: "Handler",
        list: '<div class="flex-item"></div>'
      },
      "#btn-undo": function (d,v) {
        if (null != v) this.my.undo();
      },
      "#btn-addLogger": {
        bind: function (d, v) {
          if (v != null) {
            this.my.insert("#loggers", 'after', {});
          }
        },
        events: "click.my"
      }
    },
    Handler: {
      init: function ($form) {
        $form.html(this.HandlerHTML);
      },
      ui: {
        "#name": function(d) {
          return d.name;
        },
        "#level": "level",
        "#filters": "filters"
      }
    },
    Logger: {
      init: function ($form) {
        $form.html(this.LoggerHTML);
      },
      data: {'name': 'django.db', 'level': 'DEBUG', 'handlers': [], 'filters': []},
      ui: {
        "#name": {
          bind: "name",
          check: function(data, value, $control){
            var ctr = 0;
            $.each(global_data.loggers, function(i, data) {
              if (data.name === value){
                ctr += 1;
              }
            });
            if (ctr > 1) {
              return "the logger " + value + " is overriden ";
            }
          }
        },
        "#level": "level",
        "#propagate": function (d, v) {
          if (v !== null) {
            d.propagate = v.length > 0;
          }
          return (d.propagate) ? ['true'] : [];
        },
        "#handlers": "handlers",
        "#filters": "filters",
        "#btn-removeRow": {
          bind: function (d, v) {
            if (v != null) this.my.remove();
          },
          events: "click.my"
        }
      }
    },
    MainHTML: '<div id="main_config_container">' +
    '  <h3>handlers</h3>' +
    '  <div class="flex-container" id="handlers"></div>' +
    '  <h3>loggers</h3>' +
    '  <span id="btn-addLogger" style="cursor: pointer"><strong style="color: green">+</strong> add a logger</span> ' +
    '  <div class="flex-container" >' +
    '     <table>' +
    '       <thead><tr>' +
    '         <th>name</th><th>level</th><th>propagate</th><th>handler</th><th>filter</th><th>remove</th>' +
    '       </tr></thead>' +
    '       <tbody id="loggers"></tbody>' +
    '     </table>' +
    '  </div>' +
    '  <hr />' +
    '  </div><input id="btn-undo" type="button" value="Undo"/></div>' +
    '  </div>',
    HandlerHTML: '' +
    '  <h2 id="name"></h2>' +
    '  <select id="level" >' +
    $.map(levels, function (val) {
      return '    <option value="' + val + '">' + val + '</option>';
    }).join() +
    '  </select>' +
    '  <select id="filters" multiple="multiple" size="' + (select_size) + '">' +
    $.map(filters, function (val) {
      return '    <option value="' + val + '">' + val + '</option>';
    }).join() +
    '  </select>',
    LoggerHTML: '' +
    '  <td><input id="name" type="text" placeholder="Name"/><br /><span class="my-error-tip"></span></td>' +
    '  <td><select id="level" >' +
    $.map(levels, function (val) {
      return '    <option value="' + val + '">' + val + '</option>';
    }).join() +
    '  </select></td>' +
    '  <td><input id="propagate" type="checkbox" name="propagate" value="true"></td>' +
    '  <td><select id="handlers" multiple="multiple" size="' + (select_size) + '">' +
    $.map(handlers, function (val) {
      return '    <option value="' + val + '">' + val + '</option>';
    }).join() +
    '  </select></td>' +
    '  <td><select id="filters" multiple="multiple" size="' + (select_size) + '">' +
    $.map(filters, function (val) {
      return '    <option value="' + val + '">' + val + '</option>';
    }).join() +
    '  </select></td>' +
    '  <td><span id="btn-removeRow" style="cursor:pointer; color: red;">X</span></td>' +
    ''
  };
  // Init $.my over DOM node


  anchor.my(manifest, global_data);
}
