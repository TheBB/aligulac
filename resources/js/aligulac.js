
(function(/*! Stitch !*/) {
  if (!this.require) {
    var modules = {}, cache = {}, require = function(name, root) {
      var path = expand(root, name), module = cache[path], fn;
      if (module) {
        return module.exports;
      } else if (fn = modules[path] || modules[path = expand(path, './index')]) {
        module = {id: path, exports: {}};
        try {
          cache[path] = module;
          fn(module.exports, function(name) {
            return require(name, dirname(path));
          }, module);
          return module.exports;
        } catch (err) {
          delete cache[path];
          throw err;
        }
      } else {
        throw 'module \'' + name + '\' not found';
      }
    }, expand = function(root, name) {
      var results = [], parts, part;
      if (/^\.\.?(\/|$)/.test(name)) {
        parts = [root, name].join('/').split('/');
      } else {
        parts = name.split('/');
      }
      for (var i = 0, length = parts.length; i < length; i++) {
        part = parts[i];
        if (part == '..') {
          results.pop();
        } else if (part != '.' && part != '') {
          results.push(part);
        }
      }
      return results.join('/');
    }, dirname = function(path) {
      return path.split('/').slice(0, -1).join('/');
    };
    this.require = function(name) {
      return require(name, '');
    }
    this.require.define = function(bundle) {
      for (var key in bundle)
        modules[key] = bundle[key];
    };
  }
  return this.require.define;
}).call(this)({"aligulac": function(exports, require, module) {(function() {
  var Aligulac,
    __indexOf = [].indexOf || function(item) { for (var i = 0, l = this.length; i < l; i++) { if (i in this && this[i] === item) return i; } return -1; };

  exports.Aligulac = Aligulac = {
    init: function() {
      var AutoComplete, Common, GenShort, Menu;
      AutoComplete = require('auto_complete').AutoComplete;
      Common = require('common').Common;
      GenShort = require('genshort').GenShort;
      Menu = require('menu').Menu;
      Menu.init();
      AutoComplete.init();
      Common.init();
      return GenShort.init();
    },
    init_extra: function(apps) {
      var Clocks, EventMgr, EventRes, apps_list;
      apps_list = apps.split(" ");
      if (__indexOf.call(apps_list, 'eventmgr') >= 0) {
        EventMgr = require('eventmgr').EventMgr;
        EventMgr.init();
      }
      if (__indexOf.call(apps_list, 'eventres') >= 0) {
        EventRes = require('eventres').EventRes;
        EventRes.init();
      }
      if (__indexOf.call(apps_list, 'clocks') >= 0) {
        Clocks = require('clocks').Clocks;
        return Clocks.init();
      }
    }
  };

}).call(this);
}, "auto_complete": function(exports, require, module) {(function() {
  var AutoComplete, add_extra_functions, aligulacAutocompleteTemplates, getResults, init_event_boxes, init_other, init_predictions, init_search_box;

  aligulacAutocompleteTemplates = function(obj) {
    var flag, name, race, team;
    if (obj.type === '--') {
      obj.key = '-';
      return "<a>BYE</a>";
    }
    if (!((obj.tag != null) || (obj.name != null) || (obj.fullname != null))) {
      return "<span class='autocomp-header'>" + autocomp_strings[obj.label] + "</span>";
    }
    switch (obj.type) {
      case 'player':
        obj.key = obj.tag + ' ' + obj.id;
        team = ((obj.teams != null) && obj.teams.length > 0 ? "<span class='autocomp-team pull-right'>" + obj.teams[0][0] + "</span>" : '');
        flag = (obj.country != null ? "<img src='" + (flags_dir + obj.country.toLowerCase()) + ".png' />" : '');
        race = "<img src='" + (races_dir + obj.race.toUpperCase()) + ".png' />";
        name = "<span>" + obj.tag + "</span>";
        return "<a>" + flag + race + name + team + "</a>";
      case 'team':
        obj.key = obj.name;
        return "<a>" + obj.name + "</a>";
      case 'event':
        obj.key = obj.fullname;
        return "<a>" + obj.fullname + "</a>";
    }
    return "<a>" + obj.value + "</a>";
  };

  getResults = function(term, restrict_to) {
    var deferred, url;
    if (restrict_to == null) {
      restrict_to = ['players', 'teams', 'events'];
    } else if (typeof restrict_to === 'string') {
      restrict_to = [restrict_to];
    }
    deferred = $.Deferred();
    url = '/search/json/';
    $.ajax({
      type: 'GET',
      url: url,
      dataType: 'json',
      data: {
        q: term,
        search_for: restrict_to.join(',')
      }
    }).success(function(ajaxData) {
      return deferred.resolve(ajaxData);
    });
    return deferred;
  };

  init_search_box = function() {
    return $('#search_box').autocomplete({
      source: function(request, response) {
        return $.when(getResults(request.term)).then(function(result) {
          var eventresult, playerresult, prepare_response, teamresult;
          prepare_response = function(list, type, label) {
            var x, _i, _len;
            if ((list == null) || list.length === 0) {
              return [];
            }
            for (_i = 0, _len = list.length; _i < _len; _i++) {
              x = list[_i];
              x.type = type;
            }
            return [
              {
                label: label
              }
            ].concat(list);
          };
          playerresult = prepare_response(result.players, 'player', 'Players');
          teamresult = prepare_response(result.teams, 'team', 'Teams');
          eventresult = prepare_response(result.events, 'event', 'Events');
          return response(playerresult.concat(teamresult.concat(eventresult)));
        });
      },
      minLength: 2,
      select: function(event, ui) {
        $('#search_box').val(ui.item.key).closest('form').submit();
        return false;
      },
      open: function() {
        return $('.ui-menu').width('auto');
      }
    }).data('ui-autocomplete')._renderItem = function(ul, item) {
      return $('<li></li>').append(aligulacAutocompleteTemplates(item)).appendTo(ul);
    };
  };

  init_event_boxes = function() {
    try {
      return $('.event-ac').autocomplete({
        source: function(request, response) {
          return $.when(getResults(request.term, 'events')).then(function(result) {
            var x, _i, _len, _ref;
            if ((result == null) || (result.events == null) || result.events.length === 0) {
              return [];
            }
            _ref = result.events;
            for (_i = 0, _len = _ref.length; _i < _len; _i++) {
              x = _ref[_i];
              x.type = 'event';
            }
            return response(result.events);
          });
        },
        minLength: 2,
        select: function(event, ui) {
          $('.event-ac').val(ui.item.key);
          return false;
        },
        open: function() {
          return $('.ui-menu').width('auto');
        }
      }).data('ui-autocomplete')._renderItem = function(ul, item) {
        return $('<li></li>').append(aligulacAutocompleteTemplates(item)).appendTo(ul);
      };
    } catch (_error) {}
  };

  add_extra_functions = function() {
    return $.fn.getTags = function() {
      var tagslist;
      tagslist = $(this).val().split('\n');
      if (tagslist[0] === '') {
        tagslist = [];
      }
      return tagslist;
    };
  };

  init_predictions = function() {
    var idPlayersTextArea;
    idPlayersTextArea = $("#id_players");
    idPlayersTextArea.tagsInput({
      autocomplete_opt: {
        minLength: 2,
        select: function(event, ui) {
          idPlayersTextArea.addTag(ui.item.key);
          $("#id_players_tag").focus();
          return false;
        },
        open: function() {
          return $('.ui-menu').width('auto');
        }
      },
      autocomplete_url: function(request, response) {
        return $.when(getResults(request.term, 'players')).then(function(result) {
          var p, _i, _len, _ref;
          if (result.players != null) {
            _ref = result.players;
            for (_i = 0, _len = _ref.length; _i < _len; _i++) {
              p = _ref[_i];
              p.type = 'player';
            }
            if (global_player_autocomplete_allow_byes && (request.term === 'bye' || request.term === '--')) {
              result.players = [
                {
                  type: '--'
                }
              ].concat(result.players);
            }
            return response(result.players);
          }
        });
      },
      defaultText: autocomp_strings['Players'],
      placeholderColor: '#9e9e9e',
      delimiter: '\n',
      width: '100%',
      formatAutocomplete: aligulacAutocompleteTemplates,
      removeWithBackspace: true
    });
    $("#id_players_addTag").keydown(function(event) {
      if (event.which === 13 && $("#id_players_tag").val() === "") {
        return $(this).closest("form").submit();
      }
    });
    return $("#id_players_tag").keydown(function(event) {
      var id, input, taglist;
      if (event.which === 8 && $(this).val() === "") {
        event.preventDefault();
        id = $(this).attr('id').replace(/_tag$/, '');
        input = $("#" + id);
        taglist = input.getTags();
        taglist.pop();
        input.importTags(taglist.join('\n'));
        return $(this).trigger('focus');
      }
    });
  };

  init_other = function() {
    return $('input#id_players_tag').focus(function() {
      return $(this).parent().parent().css('box-shadow', 'inset 0 1px 1px rgba(0,0,0,.075), 0 0 4px rgba(0,0,0,.4)').css('-webkit-box-shadow', 'inset 0 1px 1px rgba(0,0,0,.075), 0 0 4px rgba(0,0,0,.4)').css('border-color', '#000000');
    }).focusout(function() {
      return $(this).parent().parent().css('box-shadow', 'inset 0 1px 1px rgba(0,0,0,.075)').css('-webkit-box-shadow', 'inset 0 1px 1px rgba(0,0,0,.075)').css('border-color', '#cccccc');
    });
  };

  exports.AutoComplete = AutoComplete = {
    init: function() {
      add_extra_functions();
      init_search_box();
      init_event_boxes();
      init_predictions();
      return init_other();
    }
  };

}).call(this);
}, "clocks": function(exports, require, module) {(function() {
  var Clocks, clocks_toggle_more;

  clocks_toggle_more = function(e) {
    $(e).next().toggle();
    return $(e).find(".clock-toggle").toggleClass("right-caret").toggleClass("down-caret");
  };

  module.exports.Clocks = Clocks = {
    init: function() {
      return $(".clock-expandable").click(function() {
        return clocks_toggle_more(this);
      });
    }
  };

}).call(this);
}, "common": function(exports, require, module) {(function() {
  var Common, check_all_boxes, check_boxes, lm_toggle_visibility, toggle_block, uncheck_all_boxes, uncheck_boxes;

  toggle_block = function(id) {
    $(".lm[data-id=" + id + "]").toggle();
    $(".lma[data-id=" + id + "]").html($(".lma[data-id=" + id + "]").html() === autocomp_strings['hide'] ? autocomp_strings['show'] : autocomp_strings['hide']);
    return false;
  };

  lm_toggle_visibility = function(id) {
    $("#fix" + id).toggle();
    $("#inp" + id).toggle();
    $("#" + id + "_1").focus();
    return false;
  };

  check_all_boxes = function() {
    $('input[name|="match"]').prop('checked', true);
    return false;
  };

  uncheck_all_boxes = function() {
    $('input[name|="match"]').prop('checked', false);
    return false;
  };

  check_boxes = function(id) {
    $("input[data-match=" + id + "]").prop('checked', true);
    return false;
  };

  uncheck_boxes = function(id) {
    $("input[data-match=" + id + "]").prop('checked', false);
    return false;
  };

  module.exports.Common = Common = {
    init: function() {
      $('.lma').click(function() {
        return toggle_block($(this).data('id'));
      });
      $('.lmp').click(function() {
        return lm_toggle_visibility($(this).data('id'));
      });
      $('.check-boxes-btn').click(function() {
        return check_boxes($(this).data('match'));
      });
      $('.uncheck-boxes-btn').click(function() {
        return uncheck_boxes($(this).data('match'));
      });
      $('.check-all-btn').click(check_all_boxes);
      $('.uncheck-all-btn').click(uncheck_all_boxes);
      $('.not-unique-more').click(function() {
        $(this).toggle();
        $(this).parent().find('.not-unique-hidden-names').toggle();
        return false;
      });
      return $('.not-unique-update-player').click(function() {
        var id, input, tag, taglist, update, updateline, _this;
        _this = $(this);
        update = _this.data('update');
        updateline = _this.data('updateline');
        tag = _this.data('tag');
        id = _this.data('id');
        input = $("#" + update);
        taglist = input.getTags();
        taglist[updateline] = tag + " " + id;
        input.importTags(taglist.join('\n'));
        _this.closest('.message').toggle();
        return false;
      });
    }
  };

}).call(this);
}, "eventmgr": function(exports, require, module) {(function() {
  var EventMgr, modify;

  modify = function(pid, pname, ptype) {
    $('#parent_id_field').val(pid);
    $('#id_type').val((function() {
      switch (ptype) {
        case 'round':
          return 'round';
        case 'event':
          return 'round';
        case 'category':
          return 'category';
      }
    })());
    $('#parent_name').html(pname);
    return $('#md-eventmgr').modal();
  };

  module.exports.EventMgr = EventMgr = {
    init: function() {
      $('.tree-toggle').click(function() {
        $(this).parent().parent().next('.subtree').toggle(100);
        return false;
      });
      $('#root_btn').click(function() {
        $('input[id=parent_id_field]').val('-1');
        $('#parent_name').html('Root (N/A)');
        $('#md-eventmgr').modal();
        return false;
      });
      $('#showguide').click(function() {
        $('#guide').collapse();
        return $('#showguide').toggle();
      });
      $('.event-modify-button').click(function() {
        var id, name, type;
        name = $(this).data('event-fullname');
        id = $(this).data('event-id');
        type = $(this).data('event-type');
        return modify(id, name, type);
      });
      $('#id_predef_names').change(function() {
        if ($('#id_predef_names').prop('selectedIndex') > 0) {
          $('#id_custom_names').val('');
          return $('#id_type').val('round');
        }
      });
      return $('#id_custom_names').keypress(function() {
        if ($('#id_custom_names').val() !== '') {
          return $('#id_predef_names').prop('selectedIndex', 0);
        }
      });
    }
  };

}).call(this);
}, "eventres": function(exports, require, module) {(function() {
  var EventRes, changed_story, get_order, toggle_pp_players;

  changed_story = function() {
    var data, idx;
    idx = $('#extantstories').prop('selectedIndex');
    data = story_data[idx];
    $('#story_id').prop('value', data['idx']);
    $('#id_player').prop('value', data['player']);
    $('#st_date').datepicker('setDate', data['dt']);
    $('#id_text').prop('selectedIndex', data['text']);
    $('#id_params').prop('value', data['params']);
    $('#storynewbtn').prop('disabled', idx > 0);
    $('#storyupdbtn').prop('disabled', idx === 0);
    return $('#storydelbtn').prop('disabled', idx === 0);
  };

  get_order = function() {
    var list;
    list = $("#sortable").sortable("toArray");
    return $('#order').prop('value', list.join(','));
  };

  toggle_pp_players = function(id) {
    $("[data-placement=" + id + "]").toggle();
    return false;
  };

  module.exports.EventRes = EventRes = {
    init: function() {
      $(".pp_showbtn").click(function() {
        return toggle_pp_players($(this).data('placement'));
      });
      if ((typeof admin !== "undefined" && admin !== null) && admin) {
        if (typeof story_data !== "undefined" && story_data !== null) {
          $('#extantstories').change(changed_story);
        }
        if ((typeof has_children !== "undefined" && has_children !== null) && has_children) {
          $("#sortable").sortable();
          $("#sortable").disableSelection();
          return $('#submit-order').click(get_order);
        }
      }
    }
  };

}).call(this);
}, "genshort": function(exports, require, module) {(function() {
  var GenShort, gen_short;

  gen_short = function(path) {
    return $.get("/m/new/?url=" + encodeURIComponent(path), function(data) {
      $("#gen_short").hide();
      $("#disp_short").html("<a href=\"/m/" + data + "/\">/m/" + data + "</a>");
      return $("#disp_short").show();
    });
  };

  module.exports.GenShort = GenShort = {
    init: function() {
      return $("#gen_short").click(function() {
        return gen_short(location.href);
      });
    }
  };

}).call(this);
}, "menu": function(exports, require, module) {(function() {
  var Menu, mobile_regex, toggle_navbar_method;

  mobile_regex = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|OperaMini/i;

  toggle_navbar_method = function() {
    if (mobile_regex.test(navigator.userAgent) || $(window).width() <= 768) {
      return $('a.dropdown-toggle').off('click');
    } else {
      return $('a.dropdown-toggle').on('click', function() {
        return window.location.href = this.href;
      });
    }
  };

  module.exports.Menu = Menu = {
    init: function() {
      $(document).ready(toggle_navbar_method);
      return $(window).resize(toggle_navbar_method);
    }
  };

}).call(this);
}});
