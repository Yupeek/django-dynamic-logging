/**
 * Created by dbernard on 07/02/17.
 */


function logging_widget(anchor, data, handlers) {
  console.debug(anchor, data);
  var logger_conifg = {"loggers":[
        {"name": "django", "level":"1","handlers":["devnull"]},
        {"name": "django.db", "level":"3","handlers":["devnull"]}
      ]
    }, levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

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
      res = [];
    $.each(data.loggers || {}, function (loggername, logger) {
      logger.name = loggername;
      res.push(logger);
    });

    return {'loggers': res}
  }

  /**
   * dump the data from the form as a json encoded string
   * @param data
   * @returns {{loggers: Array}} the data of the form encoded
   */
  function dump_form(data) {
    var loggers = {}, lname;
    $.each(data.loggers, function(i, logger) {
      logger = $.extend(true, {}, logger);
      lname = logger.name;
      delete logger.name;
      loggers[lname] = logger;
    });
    return JSON.stringify({'loggers': loggers});
  }
  //JSON.parse(data.val());

  // Manifest
  var manifest = {

    // Init function
    init: function ($form, runtime) {
      $form.html(this.LoggersHTML);
      this.Logger.LoggerHTML = this.LoggerHTML;

      $form.then(function() {
          $form.on('change', function() {
            console.debug("should change json to ", JSON.stringify($form.my("data")));

            data.val(dump_form($form.my("data")));
          })
      })
    },

    // Bindings
    ui: {
      "#loggers": {
        bind: "loggers",
        manifest: "Logger",

      },
      "#btn-addRow": {
        bind: function(d,v ){
          if (v != null) {
            this.my.insert("#loggers", {});
          }
        },
        events:"click.my"
      }
    },
    Logger: {
      init: function ($form){ $form.html(this.LoggerHTML); },
      data: {'name': 'django.db', 'level': 'DEBUG'},
      ui: {
        "#name": "name",
        "#level": "level",
        "#propagate": function (d, v) {
          console.debug(d, v);
          if (v !== null) {
            d.propagate = v.length > 0;
          }
          return (d.propagate) ? ['true']: [];
        },
        "#handlers": "handlers",
        "#btn-removeRow":{
          bind: function (d,v) {
            if (v!=null) this.my.remove();
          },
          events:"click.my"
        }
      }
    },
    LoggersHTML: '<div>' +
      '<span id="btn-addRow" style="cursor: pointer"><strong style="color: green">+</strong> ajouter un logger</span> ' +
      '<div class="loggers_container" id="loggers"></div>' +
    '</div>',
    LoggerHTML: '<div class="logger">' +
      '<input id="name" type="text" placeholder="Name"/>' +
        '<select id="level" >' +
          $.map(levels, function(val) { return '<option value="'+val+'">'+val+'</option>';}).join() +
        '</select>' +
        '<input id="propagate" type="checkbox" name="propagate" value="true"> propagate</label>' +
        '<select id="handlers" multiple="multiple" size="'+(handlers.length)+'">' +
          $.map(handlers, function(val) { return '<option value="'+val+'">'+val+'</option>';}).join() +
        '</select>' +
        '<span id="btn-removeRow" style="cursor:pointer; color: red;">X</span> ' +
      '</div>'
    };
  // Init $.my over DOM node
  console.debug(data.val());
  var form_text = data.val(),
    original_data = load_form(form_text);

  anchor.my(manifest, original_data);
}
