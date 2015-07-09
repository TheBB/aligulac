
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
    indexOf = [].indexOf || function(item) { for (var i = 0, l = this.length; i < l; i++) { if (i in this && this[i] === item) return i; } return -1; };

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
      var Clocks, EventMgr, EventRes, PlayerInfo, apps_list;
      apps_list = apps.split(" ");
      if (indexOf.call(apps_list, 'eventmgr') >= 0) {
        EventMgr = require('eventmgr').EventMgr;
        EventMgr.init();
      }
      if (indexOf.call(apps_list, 'eventres') >= 0) {
        EventRes = require('eventres').EventRes;
        EventRes.init();
      }
      if (indexOf.call(apps_list, 'clocks') >= 0) {
        Clocks = require('clocks').Clocks;
        Clocks.init();
      }
      if (indexOf.call(apps_list, 'player_info') >= 0) {
        PlayerInfo = require('player_info').PlayerInfo;
        return PlayerInfo.init();
      }
    }
  };

}).call(this);
}, "auto_complete": function(exports, require, module) {(function() {
  var AutoComplete, add_extra_functions, aligulac_autocomplete_templates, getResults, init_event_boxes, init_other, init_predictions, init_search_box, load_recent_results_from_cache, save_autocomplete_object_to_cache;

  save_autocomplete_object_to_cache = function(obj) {
    var cache_obj, idx, keys, recent_result, x;
    if (obj && window.localStorage) {
      recent_result = load_recent_results_from_cache();
      if (!recent_result) {
        recent_result = [];
      }
      if (obj.type === 'cache') {
        cache_obj = obj;
      } else {
        cache_obj = {
          html: aligulac_autocomplete_templates(obj),
          key: obj.key,
          type: 'cache',
          'origin-type': obj.type + "s"
        };
      }
      keys = (function() {
        var k, len, results;
        results = [];
        for (k = 0, len = recent_result.length; k < len; k++) {
          x = recent_result[k];
          results.push(x.key);
        }
        return results;
      })();
      idx = $.inArray(obj.key, keys);
      if (idx > -1) {
        recent_result.splice(idx, 1);
      }
      while (recent_result.length >= 10) {
        recent_result.pop();
      }
      recent_result.unshift(cache_obj);
      window.localStorage.setItem('aligulac.autocomplete.caching', JSON.stringify(recent_result));
    }
  };

  load_recent_results_from_cache = function(restrict_to) {
    var i, items, j, k, l, len, len1, result;
    result = [];
    if (window.localStorage) {
      items = JSON.parse(localStorage.getItem('aligulac.autocomplete.caching'));
      if (!items) {
        return [];
      }
      if (!restrict_to) {
        return items;
      }
      for (k = 0, len = items.length; k < len; k++) {
        i = items[k];
        for (l = 0, len1 = restrict_to.length; l < len1; l++) {
          j = restrict_to[l];
          if (i['origin-type'] === j) {
            result.push(i);
          }
        }
      }
    }
    return result;
  };

  aligulac_autocomplete_templates = function(obj) {
    var flag, name, race, team;
    if (obj.type === '--') {
      obj.key = '-';
      return "<a>BYE</a>";
    }
    switch (obj.type) {
      case 'header':
        return "<span class='autocomp-header'>" + autocomp_strings[obj.label] + "</span>";
      case 'player':
        obj.key = obj.tag + " " + obj.id;
        team = (obj.teams && obj.teams.length > 0 ? "<span class='autocomp-team pull-right'>" + obj.teams[0][0] + "</span>" : '');
        flag = (obj.country ? "<img src='" + (flags_dir + obj.country.toLowerCase()) + ".png' />" : '');
        race = "<img src='" + (races_dir + obj.race.toUpperCase()) + ".png' />";
        name = "<span>" + obj.tag + "</span>";
        return "<a>" + flag + race + name + team + "</a>";
      case 'team':
        obj.key = obj.name;
        return "<a>" + obj.name + "</a>";
      case 'event':
        obj.key = obj.fullname;
        return "<a>" + obj.fullname + "</a>";
      case 'cache':
        return obj.html;
    }
  };

  getResults = function(term, restrict_to) {
    var deferred, recent_results;
    if (restrict_to == null) {
      restrict_to = ['players', 'teams', 'events'];
    } else if (typeof restrict_to === 'string') {
      restrict_to = [restrict_to];
    }
    deferred = $.Deferred();
    recent_results = load_recent_results_from_cache(restrict_to);
    if (((!term) || (term.length < 2)) && recent_results) {
      return deferred.resolve({
        cache: recent_results
      });
    }
    $.get('/search/json/', {
      q: term,
      search_for: restrict_to.join(',')
    }).success(function(ajaxData) {
      if (recent_results) {
        ajaxData.cache = recent_results;
      }
      return deferred.resolve(ajaxData);
    });
    return deferred;
  };

  init_search_box = function() {
    var $searchbox;
    $searchbox = $('#search_box');
    $searchbox.bind('focus', function() {
      return $(this).autocomplete('search');
    });
    return $searchbox.autocomplete({
      source: function(request, response) {
        return $.when(getResults(request.term)).then(function(result) {
          var cacheresult, eventresult, playerresult, prepare_response, teamresult;
          prepare_response = function(list, type, label) {
            var k, len, x;
            if (!list || list.length === 0) {
              return [];
            }
            for (k = 0, len = list.length; k < len; k++) {
              x = list[k];
              x.type = type;
            }
            return [
              {
                label: label,
                type: 'header'
              }
            ].concat(list);
          };
          playerresult = prepare_response(result.players, 'player', 'Players');
          teamresult = prepare_response(result.teams, 'team', 'Teams');
          eventresult = prepare_response(result.events, 'event', 'Events');
          cacheresult = prepare_response(result.cache, 'cache', 'Your recent searches');
          return response(playerresult.concat(teamresult.concat(eventresult.concat(cacheresult))));
        });
      },
      minLength: 0,
      select: function(event, ui) {
        save_autocomplete_object_to_cache(ui.item);
        $searchbox.val(ui.item.key).closest('form').submit();
        return false;
      },
      open: function() {
        return $('.ui-menu').width('auto');
      }
    }).data('ui-autocomplete')._renderItem = function(ul, item) {
      return $('<li></li>').append(aligulac_autocomplete_templates(item)).appendTo(ul);
    };
  };

  init_event_boxes = function() {
    try {
      return $('.event-ac').autocomplete({
        source: function(request, response) {
          return $.when(getResults(request.term, 'events')).then(function(result) {
            var k, len, ref, x;
            if ((result == null) || (result.events == null) || result.events.length === 0) {
              return [];
            }
            ref = result.events;
            for (k = 0, len = ref.length; k < len; k++) {
              x = ref[k];
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
        return $('<li></li>').append(aligulac_autocomplete_templates(item)).appendTo(ul);
      };
    } catch (_error) {}
  };

  add_extra_functions = function() {
    return $.fn.getTags = function() {
      var tagslist;
      tagslist = $(this).val().split('\n');
      if (tagslist[0] === '') {
        return [];
      }
      return tagslist;
    };
  };

  init_predictions = function() {
    var idPlayersTextArea;
    idPlayersTextArea = $("#id_players");
    idPlayersTextArea.tagsInput({
      autocomplete_opt: {
        minLength: 0,
        select: function(event, ui) {
          save_autocomplete_object_to_cache(ui.item);
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
          var k, len, p, ref;
          if (result.players) {
            ref = result.players;
            for (k = 0, len = ref.length; k < len; k++) {
              p = ref[k];
              p.type = 'player';
            }
            if (global_player_autocomplete_allow_byes && (request.term === 'bye' || request.term === '--')) {
              result.players = [
                {
                  type: '--'
                }
              ].concat(result.players);
            }
          } else {
            result.players = [];
          }
          result.cache.unshift({
            value: autocomp_strings['Your_recent_searches']
          });
          return response(result.players.concat(result.cache));
        });
      },
      defaultText: autocomp_strings['Players'],
      placeholderColor: '#9e9e9e',
      delimiter: '\n',
      width: '100%',
      formatAutocomplete: aligulac_autocomplete_templates,
      removeWithBackspace: true
    });
    $('#id_players_addTag').keydown(function(event) {
      if (event.which === 13 && $('#id_players_tag').val() === '') {
        return $(this).closest("form").submit();
      }
    });
    return $('#id_players_tag').keydown(function(event) {
      var id, input, taglist;
      if (event.which === 8 && $(this).val() === '') {
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

  module.exports.create_tag = function(tag) {
    return $(document.createElement(tag));
  };

  module.exports.Common = Common = {
    init: function() {
      $('.langbtn').click(function() {
        return $(this).closest('form').submit();
      });
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
        var _this, id, input, tag, taglist, update, updateline;
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
}, "player_info": function(exports, require, module) {(function() {
  var PlayerInfo, create_tag, get_player_info, toggle_form;

  create_tag = require('common').create_tag;

  toggle_form = function(sender) {
    var data, i, k, k2, keys, lbl, len, lp, val;
    data = function(x) {
      return $(sender).closest('tr').data(x);
    };
    keys = ['id', 'country', 'birthday', 'name', 'romanized-name'];
    for (i = 0, len = keys.length; i < len; i++) {
      k = keys[i];
      val = data(k);
      k2 = k.replace('-', '_');
      $("#id_" + k2).val(val);
      if (k2 === "id") {
        continue;
      }
      lbl = $("label[for=id_" + k2 + "]");
      if (lbl.children("small").length === 0) {
        lbl.append(create_tag('small').attr("id", "id_" + k2 + "_small").css({
          "font-weight": "normal"
        }).hide());
      } else {
        lbl.children("small").empty().hide();
      }
    }
    lp = data('lp');
    if ((lp != null) && lp !== "") {
      $("#get_lp_btn").data('lp', lp);
      $("#get_lp_btn").show();
      $("#get_lp_span").show();
      return $("#get_lp_span").children("small").text(autocomp_strings["Loading..."]).hide();
    } else {
      $("#get_lp_btn").data('lp', null);
      $("#get_lp_btn").hide();
      return $("#get_lp_span").hide();
    }
  };

  get_player_info = function(lp) {
    $("#get_lp_span").children().toggle();
    return $.getJSON("/add/player_info_lp/?title=" + (escape(lp)), function(_data) {
      var c, data, i, k, keys, len, n, o;
      if (_data.data == null) {
        $("#get_lp_span").children("small").text(autocomp_strings[_data.message]);
        return;
      }
      data = _data.data;
      keys = ['name', 'romanized_name', 'birthday'];
      for (i = 0, len = keys.length; i < len; i++) {
        k = keys[i];
        if (data[k] != null) {
          o = $("#id_" + k).val();
          n = data[k];
          if (o !== n) {
            $("#id_" + k).val(n);
            $("#id_" + k + "_small").text(autocomp_strings["Old value"] + ": " + o).show();
            c = $("#id_" + k).css('background-color');
            $("#id_" + k).animate({
              'background-color': 'rgb(144, 238, 144)'
            }, 100).delay(750).animate({
              'background-color': c
            }, 600);
          } else {
            $("#id_" + k + "_small").hide();
          }
        }
      }
      return $("#get_lp_span").children().toggle();
    });
  };

  module.exports.PlayerInfo = PlayerInfo = {
    init: function() {
      $('.player-info-edit-button').click(function() {
        return toggle_form(this);
      });
      $('#country_filter').change(function() {
        return $(this).closest('form').submit();
      });
      return $("#get_lp_btn").click(function() {
        get_player_info($(this).data('lp'));
        return false;
      });
    }
  };

}).call(this);
}});
